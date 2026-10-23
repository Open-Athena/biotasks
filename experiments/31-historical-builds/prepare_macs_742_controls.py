"""Freeze one exported PR742 package and an unchanged 300s nop/oracle pair."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'inputs-private/macs-742-export'
SLUG = 'macs3-project__MACS'
TASK = SLUG + '-742'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    exported = json.loads((ROOT / 'macs-742-export-manifest.json').read_text())
    assert exported['task_id'] == TASK and exported['f2p_count'] == 1 and exported['p2p_count'] == 10
    assert exported['verifier_timeout_seconds'] == 300 and exported['harbor_control_run'] is False
    original = PRIVATE / 'task' / TASK
    assert original.is_dir()
    config = tomllib.loads((original / 'task.toml').read_text())
    assert config['verifier']['timeout_sec'] == 300
    files = []
    total = 0
    for row in exported['files']:
        source = PRIVATE / row['path']
        assert source.is_file() and not source.is_symlink()
        assert source.is_relative_to(original)
        assert sha(source) == row['sha256'] and source.stat().st_size == row['bytes']
        relative = source.relative_to(original)
        dest = Path('outputs') / SLUG / TASK / relative
        assert '..' not in dest.parts
        total += row['bytes']
        files.append({'path': str(dest), 'bytes': row['bytes'], 'sha256': row['sha256'], 'mode': row['mode']})
    assert len(files) == 10 and total < 10 * 1024**2
    plan = {'scope': 'One pinned Repo2RLEnv candidate export; original Harbor 300s nop/oracle controls only',
            'repositories': [{'repo': 'macs3-project/MACS', 'slug': SLUG,
                              'tasks': [{'task': TASK, 'original_files': files, 'proposed_arms_seconds': [300]}]}],
            'model_calls': 0, 'task_repairs': 0}
    plan_path = ROOT / 'macs-742-control-plan.json'
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan
    else:
        plan_path.write_text(json.dumps(plan, indent=2) + '\n')
    archive = PRIVATE / 'original-tasks.tar.gz'
    if not archive.exists():
        with archive.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as gz, tarfile.open(fileobj=gz, mode='w') as tar:
            for row in files:
                source = original / Path(row['path']).relative_to(Path('outputs') / SLUG / TASK)
                info = tarfile.TarInfo(row['path'])
                info.size = row['bytes']
                info.mode = int(row['mode'], 8)
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with source.open('rb') as stream:
                    tar.addfile(info, stream)
        archive.chmod(0o600)
    with tarfile.open(archive) as tar:
        members = [m for m in tar if m.isfile()]
        assert [m.name for m in members] == [row['path'] for row in files]
        for member, row in zip(members, files, strict=True):
            assert member.size == row['bytes'] and format(member.mode, '03o') == row['mode']
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == row['sha256']
    receipt = {'task_id': TASK, 'task_file_count': len(files), 'task_total_bytes': total,
               'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
               'control_plan_sha256': sha(plan_path), 'export_manifest_sha256': sha(ROOT / 'macs-742-export-manifest.json'),
               'verifier_timeout_seconds': 300, 'agents': ['nop', 'oracle'], 'model_calls': 0,
               'limits': ['Control task is a candidate export from archived inputs, not a fresh official generate CLI run',
                          'No Harbor execution yet; image remains retained only for this check and cleanup']}
    (ROOT / 'macs-742-control-inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'limits'}))


if __name__ == '__main__':
    main()
