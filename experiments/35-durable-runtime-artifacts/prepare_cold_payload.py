"""Freeze the already prepared native task and bounded runtime infrastructure."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parent


def main():
    dest = ROOT/'inputs-private/cold-payload'
    assert not dest.exists(), 'Never overwrite a checkpointed payload'
    manifest = json.loads((ROOT/'cold-worker-inputs.json').read_text())
    archive = ROOT/'inputs-private/cold-worker-inputs.tar.gz'
    assert archive.stat().st_size == manifest['archive_bytes']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256']
    expected = {f['path']: f for f in manifest['files']}
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) == len(expected) == 10
        assert {m.name for m in members} == set(expected)
        for member in members:
            spec = expected[member.name]
            assert member.isfile() and member.size == spec['bytes'] and member.mode == int(spec['mode'], 8)
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == spec['sha256']
    sources = {name: ROOT/name for name in ['cold_worker_job.py', 'harbor_docker_cold.py',
        'cleanup_owned.py', 'run_existing_controls.py', 'setup_controller.sh', 'cold-worker-inputs.json']}
    sources.update({'pins.json': ROOT/'control-pins.json', 'control-plan.json': ROOT/'cold-worker-control-plan.json',
        'original-tasks.tar.gz': archive, 'original-workers.json': ROOT/'inputs-private/original-workers.json'})
    assert sum(p.stat().st_size for p in sources.values()) < 256*1024
    dest.mkdir(parents=True, mode=0o700)
    for name, path in sources.items():
        assert not path.is_symlink()
        shutil.copyfile(path, dest/name)
    result = dict(run_id='biotasks35-cobrapy-1482-inline-001',
        sha256={name: hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in sources},
        model_calls=0, task_repairs=0, maximum_cpu_hours=4,
        adaptations=['Existing CPU/memory/network envelope and run ownership',
            'One ownership LABEL after FROM in an infrastructure copy only; no task commands changed',
            'Read-only source/dependency identity probe before each control',
            'Different worker selection, original-image absence checks, evidence capture and owned cleanup'])
    for path in (dest/'cold-payload.json', ROOT/'cold-payload-manifest.json'):
        path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(payload_files=len(sources)+1, task_files=10, submitted=False)))


if __name__ == '__main__':
    main()
