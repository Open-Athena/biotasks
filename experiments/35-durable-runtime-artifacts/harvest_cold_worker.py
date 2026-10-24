"""Verify immutable output bytes and report negative as well as positive controls."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

import zstandard

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks35-cobrapy-1482-inline-001'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return path


def read_control_rows(controls):
    rows = []
    for control in controls:
        assert control['task'] == 'opencobra__cobrapy-1482'
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

def classify_pair(rows, seconds=300):
    sides={r['agent']:r for r in rows if r['verifier_timeout_seconds']==seconds}
    complete=set(sides)=={'nop','oracle'} and all(r['state']=='completed' and r['wrapper_exit']==0 and r['trial_record_present'] and r['reward_details_present'] and not r['exception_present'] and r['parse_status']=='ok' for r in sides.values())
    positive=complete and sides['nop']['reward']==0 and sides['oracle']['reward']==1 and sides['oracle']['resolved'] is True
    regressions=complete and all(r['p2p_total'] is not None and r['p2p_passed']==r['p2p_total'] for r in sides.values())
    return {'verifier_timeout_seconds':seconds,'complete_parseable_pair':complete,'positive_control_pair':positive,
              'clean_oracle_command':bool(complete and sides['oracle']['command_resolved'] is True),
              'all_regression_tests_pass_both':regressions}


def main():
    account = json.loads((ROOT/'cold-accounting.json').read_text())
    assert account['job_id'] == '/exedev/'+RUN and account['attempts'] == 1
    assert account['state'] in ('succeeded', 'failed')
    output = account['output_archive']
    assert output['state'] == 'uploaded' and output['size_bytes'] < 8*1024**2
    dest = ROOT/'inputs-private/cold-output'
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    archive = dest/'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud', 'storage', 'cp', '--quiet',
            output['uri'], str(archive)], capture_output=True, check=True, timeout=90)
    assert archive.stat().st_size == output['size_bytes'] and sha(archive) == output['sha256']
    seen, members, total = set(), [], 0
    with archive.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            path = safe(member.name)
            if member.isdir():
                continue
            assert member.isfile() and member.name not in seen and member.size < 8*1024**2
            seen.add(member.name)
            total += member.size
            assert total < 16*1024**2
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
    report = json.loads((dest/'control-result.json').read_text())
    assert report['run_id'] == RUN and report['model_calls'] == 0
    assert report['payload_sha256'] == json.loads((ROOT/'cold-payload-manifest.json').read_text())['sha256']
    for name, value in report.get('output_sha256', {}).items():
        assert sha(dest/safe(name)) == value
    inputs = json.loads((ROOT/'cold-worker-inputs.json').read_text())
    expected = {row['path']: row['sha256'] for row in inputs['files']}
    unchanged_path = dest/'controls/task-files-unchanged.json'
    unchanged = json.loads(unchanged_path.read_text()) if unchanged_path.exists() else {}
    task_verified = bool(unchanged.get('verified') and unchanged['before'] == unchanged['after'] == expected)
    controls_path = dest/'controls/controls.json'
    controls = json.loads(controls_path.read_text()) if controls_path.exists() else []
    rows = read_control_rows(controls)
    pair = classify_pair(rows)
    identities = report.get('image_identities', [])
    builds_path = dest/'bounded-builds.jsonl'
    builds = [json.loads(line) for line in builds_path.read_text().splitlines()] if builds_path.exists() else []
    identity_bound = (len(identities) == len(builds) == len(controls) == 2
        and all(r['git_head'] == inputs['base_commit'] for r in identities)
        and all(b['exit_code'] == 0 and b.get('image_id') for b in builds)
        and all(i['image'] == b['image'] and b['dockerfile_sha256'] == i['dockerfile_sha256']
                and control['started'] <= b['started'] < b['finished'] < i['captured'] <= control['finished']
                for i, b, control in zip(identities, builds, controls)))
    raw_logs=[]
    package_path=dest/'control-artifacts.tar.gz'
    packaged_files={}
    if package_path.exists():
        with tarfile.open(package_path) as tar:
            for member in tar:
                safe(member.name)
                if member.isdir():continue
                assert member.isfile() and member.size<1024**2 and member.name not in packaged_files
                packaged_files[member.name]=(tar.extractfile(member).read(),member.mode)
        assert {n for n in packaged_files if n.startswith('outputs/')}==set(expected)
        for spec in inputs['files']:
            data,mode=packaged_files[spec['path']]
            assert hashlib.sha256(data).hexdigest()==spec['sha256'] and mode==int(spec['mode'],8)
        from harbor_docker_cold import tagged_recipe
        recipe_name=next(n for n in expected if n.endswith('/Dockerfile'))
        recipe=packaged_files[recipe_name][0]
        effective=tagged_recipe(recipe,RUN)
        assert packaged_files['infra/'+hashlib.sha256(recipe).hexdigest()+'.Dockerfile'][0]==effective
        assert all(b['effective_dockerfile_sha256']==hashlib.sha256(effective).hexdigest() for b in builds)
        for control,row in zip(controls,rows):
            arm=control['agent']
            prefix='jobs/cobrapy-1482-controls/'
            trial=control['trial_results'][0]
            assert json.loads(packaged_files[prefix+trial['path']][0])==trial['result']
            for name,value in control['reward_files'].items():
                assert packaged_files[prefix+name][0].decode()==value
            logs=[(name,data.decode()) for name,(data,_) in packaged_files.items()
                  if '-300s-'+arm+'/' in name and name.endswith('/verifier/test-stdout.txt')]
            assert len(logs)==1
            name,text=logs[0]
            counts='2 failed, 17 passed' if arm=='nop' else '19 passed'
            assert re.search(r'=+ '+counts+r' in [0-9.]+s =+',text)
            raw_logs.append(dict(agent=arm,path=name,summary=counts,
                                 sha256=hashlib.sha256(text.encode()).hexdigest()))
    absence_verified = report.get('original_image_absence') == {ref: True for ref in inputs['original_worker_state_refs']}
    submission = json.loads((ROOT/'run-private'/RUN/'submission.json').read_text())
    worker_verified = bool(report.get('different_worker_verified') and report.get('worker_id') == submission['worker_id'])
    base = report.get('public_base_inspect') or {}
    result = dict(run_id=RUN, job_state=account['state'], archive_sha256=sha(archive), archive_members=members,
        task=inputs['task'], original_task_identity=inputs['original_task_identity'],
        prepared_task_identity=inputs['prepared_task_identity'], task_files_verified=task_verified,
        different_worker_verified=worker_verified, original_images_absent=absence_verified,
        actual_image_provenance_verified=bool(identity_bound), actual_builds=builds,
        distinct_built_image_ids=len({b.get('image_id') for b in builds}),
        raw_test_logs_verified=raw_logs,
        dependencies_match_both_arms=bool(len(identities) == 2 and all(identities[0][k] == identities[1][k] for k in ['python','platform','packages'])),
        public_base_id=base.get('Id'), public_base_repo_digests=base.get('RepoDigests'),
        rows=rows, pair=pair, model_calls=0, task_repairs=0,
        owned_resources_removed=report.get('cleanup', {}).get('verified_empty', False),
        allocated_cpu_hours=account['allocated_cpu_hours'],
        limits=['One existing task, one different-worker attempt; no cohort-wide portability claim',
            'Native clean recipe uses mutable public dependencies; no image byte-identity claim',
            'Registry distribution and other prepared exports remain untested'])
    (ROOT/'cold-readback.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('archive_members','actual_builds','limits')}))


if __name__ == '__main__':
    main()

