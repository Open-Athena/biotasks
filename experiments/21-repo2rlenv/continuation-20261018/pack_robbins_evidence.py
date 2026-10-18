"""Retain one complete native task and lossless, checked control deltas.

Run only after control execution. This removes redundant task copies, not test
results or unique task bytes. The saved original manifest and per-case solution
scripts reconstruct every control with its original hashes and permissions.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def inventory(root):
    records = {}
    for file in sorted(root.rglob('*')):
        if file.is_symlink():
            raise ValueError('Unexpected linked task asset')
        if file.is_file():
            with file.open('rb') as stream:
                sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            records[file.relative_to(root).as_posix()] = {'sha256': sha, 'mode': oct(file.stat().st_mode & 0o777)}
    return records


def restore(root, output, case):
    record = json.loads((root / 'canonical-task-storage.json').read_text())
    shutil.copytree(root / 'native-task', output)
    for relative in record['profile_deleted_assets']:
        (output / relative).unlink()
    for relative in record['profile_changed_assets']:
        source = root / 'profile-delta' / relative
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(root / 'control-deltas' / case / 'solve.sh', output / 'solution/solve.sh')
    return output


def canonicalize(root):
    manifest = json.loads((root / 'control-manifest.json').read_text())
    native = inventory(root / 'native-task')
    profile = inventory(root / 'offline-task')
    assert native == manifest['native_assets']
    assert profile == manifest['profile_assets']
    changed = sorted(k for k, v in profile.items() if native.get(k) != v)
    deleted = sorted(set(native) - set(profile))
    assert set(changed) <= {'task.toml'}
    assert set(deleted) <= {'environment/docker-compose.yaml'}
    for relative in changed:
        destination = root / 'profile-delta' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / 'offline-task' / relative, destination)
    expected = {}
    for case in manifest['cases']:
        name = case['case']
        directory = root / 'cases' / name
        hashes = inventory(directory)
        assert {k: v for k, v in hashes.items() if k != 'solution/solve.sh'} == manifest['case_unchanged_assets']
        destination = root / 'control-deltas' / name / 'solve.sh'
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(directory / 'solution/solve.sh', destination)
        expected[name] = hashes
    record = {'stage': 'lossless_control_storage_before_archive', 'complete_native_task': 'native-task', 'original_control_manifest': 'control-manifest.json', 'profile_changed_assets': changed, 'profile_deleted_assets': deleted, 'control_solution_paths': {name: 'control-deltas/' + name + '/solve.sh' for name in expected}, 'restored_control_hashes_and_permissions_verified': [], 'unique_task_source_or_grade_bytes_removed': False, 'model_calls': 0}
    path = root / 'canonical-task-storage.json'
    path.write_text(json.dumps(record, indent=2) + '\n')
    # Exercise the restoration from retained bytes before deleting any copy.
    for case in manifest['cases']:
        name = case['case']
        with tempfile.TemporaryDirectory(prefix='robbins-control-restore-') as temporary:
            restored = restore(root, Path(temporary) / 'task', name)
            assert inventory(restored) == expected[name]
        record['restored_control_hashes_and_permissions_verified'].append(name)
    path.write_text(json.dumps(record, indent=2) + '\n')
    shutil.rmtree(root / 'offline-task')
    shutil.rmtree(root / 'cases')
    assert inventory(root / 'native-task') == native
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--restore-case')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.restore_case:
        if args.output is None:
            parser.error('--output required for restoration')
        restore(args.root, args.output, args.restore_case)
    else:
        print(json.dumps(canonicalize(args.root)))
