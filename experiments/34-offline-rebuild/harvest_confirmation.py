"""Verify the combined job archive and classify its frozen controls; no rerun."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

import zstandard

from capture_build_receipt import validate_receipt
from harvest_macs_742_controls import classify_pair

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks34-macs-742-confirm-001'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return path


def read_control_rows(controls):
    rows = []
    for control in controls:
        assert control['task'] == 'macs3-project__MACS-742'
        assert control['agent'] in ('nop', 'oracle') and control['verifier_timeout_seconds'] == 300
        trials = control.get('trial_results', [])
        assert len(trials) <= 1
        trial = trials[0]['result'] if trials else {}
        details = [json.loads(value) for name, value in control.get('reward_files', {}).items() if name.endswith('reward-details.json')]
        assert len(details) <= 1
        detail = details[0] if details else {}
        rows.append(dict(task=control['task'], agent=control['agent'], verifier_timeout_seconds=300,
            state=control['state'], wrapper_exit=control.get('exit_code'), trial_record_present=bool(trial),
            reward_details_present=bool(details), exception_present=bool(trial.get('exception_info')),
            reward=((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
            parse_status=detail.get('parse_status'), resolved=detail.get('resolved'),
            command_resolved=detail.get('command_resolved'), test_exit_code=detail.get('exit_code'),
            f2p_passed=detail.get('f2p_passed'), f2p_total=detail.get('f2p_total'),
            p2p_passed=detail.get('p2p_passed'), p2p_total=detail.get('p2p_total')))
    assert len({r['agent'] for r in rows}) == len(rows) <= 2
    return rows


def main():
    account = json.loads((ROOT/'confirmation-accounting.json').read_text())
    assert account['job_id'] == '/exedev/'+RUN and account['state'] in ('succeeded', 'failed')
    assert account['attempts'] == 1 and account['model_calls'] == 0
    output = account['output_archive']
    assert output['state'] == 'uploaded' and output['size_bytes'] < 16*1024**2
    dest = ROOT/'inputs-private/confirmation-output'
    dest.mkdir(parents=True, mode=0o700, exist_ok=True)
    archive = dest/'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud', 'storage', 'cp', '--quiet',
            output['uri'], str(archive)], check=True, capture_output=True, timeout=90)
    assert archive.stat().st_size == output['size_bytes'] and sha(archive) == output['sha256']
    members = []
    seen = set()
    total = 0
    with archive.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            path = safe_path(member.name)
            if member.isdir():
                continue
            assert member.isfile() and member.name not in seen and member.size < 16*1024**2
            seen.add(member.name)
            total += member.size
            assert total < 64*1024**2
            data = tar.extractfile(member).read()
            assert len(data) == member.size
            target = dest/path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert not target.is_symlink() and target.read_bytes() == data
            else:
                target.write_bytes(data)
                target.chmod(0o600)
            members.append(dict(path=member.name, bytes=member.size, sha256=sha(target)))
    report = json.loads((dest/'confirmation-result.json').read_text())
    assert report['run_id'] == RUN and report['model_calls'] == report['task_repairs'] == 0
    payload = json.loads((ROOT/'confirmation-payload-manifest.json').read_text())
    assert report['payload_sha256'] == payload['sha256']
    for name, value in report['output_sha256'].items():
        assert sha(dest/safe_path(name)) == value
    reconstruction_path = dest/'reconstruction/macs-longcheck-result.json'
    image = json.loads(reconstruction_path.read_text()) if reconstruction_path.exists() else {}
    recipe = json.loads((ROOT/'inputs-private/macs-recorded-replay.json').read_text())
    for action, original in zip((image.get('replay') or {}).get('steps', []), recipe['actions'], strict=False):
        assert all(action[key] == original[key] for key in ('step', 'command_sha256', 'expected_exit_code', 'timeout_seconds'))
    native = bool(image.get('smoke_passed') and image.get('verify_passed') and image.get('cleanup_verified')
        and (image.get('replay') or {}).get('status') == 'matched_recorded_exits')
    control_path = dest/'controls/control-result.json'
    control_report = json.loads(control_path.read_text()) if control_path.exists() else {}
    if control_report:
        assert control_report['run_id'] == RUN and control_report['model_calls'] == 0
    for name, value in control_report.get('output_sha256', {}).items():
        assert sha(dest/'controls'/safe_path(name)) == value
    plan_path = dest/'control-plan.json'
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    expected = {f['path']: f['sha256'] for repo in plan.get('repositories', []) for task in repo['tasks'] for f in task['original_files']}
    unchanged_path = dest/'controls/controls/task-files-unchanged.json'
    unchanged = json.loads(unchanged_path.read_text()) if unchanged_path.exists() else {}
    task_verified = bool(unchanged.get('verified') and len(expected) == 12
        and unchanged['before'] == unchanged['after'] == expected)
    if plan:
        assert sha(plan_path) == report['candidate']['control_plan_sha256']
        manifest_path = dest/'candidate-manifest.json'
        assert sha(manifest_path) == report['candidate']['candidate_manifest_sha256']
        manifest = json.loads(manifest_path.read_text())
        assert manifest['image_id'] == image['retained_image_id'] and manifest['unchanged_original_files'] == 9
    receipt_rows = []
    declaration = json.loads((ROOT/'macs-base-dependency-plan.json').read_text())
    for item in control_report.get('dependency_receipts', []):
        path = dest/'controls'/safe_path(item['file'])
        assert sha(path) == item['sha256'] and item['captured_before_task_start'] is True
        receipt = json.loads(path.read_text())
        validate_receipt(receipt)
        for key in ('base_commit', 'target_distribution', 'pyproject_sha256', 'build_requirements', 'build_backend'):
            assert receipt['plan'][key] == declaration[key]
        receipt_rows.append(dict(item, receipt=receipt))
    controls_path = dest/'controls/controls/controls.json'
    controls = json.loads(controls_path.read_text()) if controls_path.exists() else []
    rows = read_control_rows(controls)
    pair = classify_pair(rows)
    image_bound = bool(image.get('retained_image_id') and control_report.get('bootstrap_image_id') == image['retained_image_id'])
    result = dict(run_id=RUN, job_state=account['state'], archive_sha256=sha(archive), archive_members=members,
        reconstruction_verified=native, candidate_files_verified=task_verified, bootstrap_image_bound=image_bound,
        dependency_receipts=receipt_rows, dependency_preparation_verified=len(receipt_rows) == 2,
        rows=rows, pair=pair, model_calls=0, task_repairs=0, allocated_cpu_hours=account['allocated_cpu_hours'],
        owned_control_resources_removed=control_report.get('cleanup', {}).get('verified_empty', False),
        retained_image_id=image.get('retained_image_id'), retained_image_tag=image.get('retained_image_tag'),
        limits=['Separate reconstructed environment and control attempt, not another unique task',
            'Dependency hashes establish provenance; image bytes are not archived',
            'Negative or missing control evidence remains explicit', 'Owned reconstruction image requires separate cleanup after archival'])
    (ROOT/'confirmation-readback.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('archive_members', 'dependency_receipts', 'limits')}))


if __name__ == '__main__':
    main()
