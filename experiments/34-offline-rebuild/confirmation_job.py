"""One bounded no-model reconstruction -> frozen candidate -> control job.

Preserve evidence and the reconstruction image for external verified archival
and separately admitted cleanup. Never retry or repair a failed stage.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

from prepare_control_variant import prepare

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks34-macs-742-confirm-001'
OUT = Path(os.environ.get('IRIS_OUTPUT_DIR', '/unused'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unpack_original(archive, plan, destination):
    specs = {f['path']: f for repo in plan['repositories'] for task in repo['tasks'] for f in task['original_files']}
    assert len(specs) == 10
    seen = set()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            if member.isdir():
                continue
            assert member.isfile() and member.name in specs and member.name not in seen
            path = Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            spec = specs[member.name]
            assert member.size == spec['bytes'] and member.size < 1024**2
            raw = tar.extractfile(member).read()
            assert hashlib.sha256(raw).hexdigest() == spec['sha256']
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists()
            target.write_bytes(raw)
            target.chmod(int(spec['mode'], 8))
            seen.add(member.name)
    assert seen == set(specs)


def package_candidate(original, plan_path, image):
    workspace = ROOT / 'candidate'
    destination = workspace / 'outputs/macs3-project__MACS/macs3-project__MACS-742'
    destination.parent.mkdir(parents=True)
    plan, manifest = prepare(original, plan_path, image, destination)
    (ROOT / 'control-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (OUT / 'candidate-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT / 'control-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    archive = ROOT / 'original-tasks.tar.gz'
    with archive.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode='w|') as tar:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                member = tar.gettarinfo(str(path), arcname=str(path.relative_to(workspace)))
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ''
                with path.open('rb') as stream:
                    tar.addfile(member, stream)
    # Independent archive inventory/hash verification before control execution.
    expected = {f['path']: f for f in manifest['task_files']}
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) == len(expected) == 12 and {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and member.size == expected[member.name]['bytes']
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == expected[member.name]['sha256']
    return dict(archive_sha256=sha(archive), control_plan_sha256=sha(ROOT/'control-plan.json'),
                candidate_manifest_sha256=sha(OUT/'candidate-manifest.json'), files=12)


def main():
    assert os.environ['BIOTASKS_RUN_ID'] == RUN
    assert not any(os.environ.get(k) for k in ('OPENROUTER_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN', 'CW_KEY_SECRET'))
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(run_id=RUN, model_calls=0, task_repairs=0, started=time.time(), stages=[])
    try:
        pins = json.loads((ROOT/'confirmation-payload.json').read_text())
        for name, expected in pins['sha256'].items():
            assert sha(ROOT/name) == expected
        report['payload_sha256'] = pins['sha256']
        original_plan = json.loads((ROOT/'original-control-plan.json').read_text())
        unpack_original(ROOT/'original-export.tar.gz', original_plan, ROOT/'original')
        reconstruction = OUT/'reconstruction'
        reconstruction.mkdir()
        env = dict(os.environ, BIOTASKS_RUN_ID=RUN+'-image', IRIS_OUTPUT_DIR=str(reconstruction))
        with (OUT/'reconstruction.log').open('w') as log:
            result = subprocess.run([sys.executable, str(ROOT/'confirmation_replay.py')], env=env,
                stdout=log, stderr=subprocess.STDOUT, timeout=3300)
        report['stages'].append(dict(stage='reconstruction', exit_code=result.returncode))
        assert result.returncode == 0
        image = json.loads((reconstruction/'macs-longcheck-result.json').read_text())
        assert image['smoke_passed'] and image['verify_passed'] and image['cleanup_verified']
        assert image['replay']['status'] == 'matched_recorded_exits' and image['owned_containers_absent']
        report['retained_image_id'] = image['retained_image_id']
        report['retained_image_tag'] = image['retained_image_tag']
        original = ROOT/'original/outputs/macs3-project__MACS/macs3-project__MACS-742'
        report['candidate'] = package_candidate(original, ROOT/'original-control-plan.json', image['retained_image_id'])
        (ROOT/'reconstruction-result.json').write_text(json.dumps(dict(retained_image=image['retained_image_tag'], image_id=image['retained_image_id']))+'\n')
        controls = OUT/'controls'
        controls.mkdir()
        env = dict(os.environ, IRIS_OUTPUT_DIR=str(controls))
        with (OUT/'controls.log').open('w') as log:
            result = subprocess.run([sys.executable, str(ROOT/'confirmation_control_supervisor.py')], env=env,
                stdout=log, stderr=subprocess.STDOUT, timeout=3300)
        report['stages'].append(dict(stage='controls', exit_code=result.returncode))
        assert result.returncode == 0
        report['execution_completed'] = True
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['error'] = str(error)[:500]
    finally:
        report['finished'] = time.time()
        report['output_sha256'] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob('*') if p.is_file() and p.name != 'confirmation-result.json'}
        (OUT/'confirmation-result.json').write_text(json.dumps(report, indent=2)+'\n')
        print('BIOTASKS34_CONFIRMATION='+json.dumps(report), flush=True)
    assert report.get('execution_completed'), 'Preserve failure; no automatic retry'


if __name__ == '__main__':
    main()
