"""Archive controls without duplicating unchanged, previously archived task assets."""
import hashlib
import json
import tarfile
from pathlib import Path


def pack(root: Path, target: Path):
    bundles = root / 'independent/bundles'
    manifest = json.loads((bundles / 'manifest.json').read_text())
    omitted = set()
    for case in manifest['cases']:
        name = case['case']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid case name')
        bundle = bundles / name
        actual = {}
        for path in bundle.rglob('*'):
            if path.is_symlink():
                raise ValueError('Linked control asset')
            if path.is_file():
                rel = path.relative_to(bundle).as_posix()
                if rel != 'solution/solve.sh':
                    with path.open('rb') as stream:
                        actual[rel] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != manifest['unchanged_assets']:
            raise ValueError('Control assets differ from original manifest')
        omitted.update((bundle / rel).relative_to(root).as_posix() for rel in actual)
    receipt = {
        'source_bundle_hash': manifest['source_bundle_hash'],
        'omitted_duplicate_files': len(omitted),
        'reconstruction': 'Restore unchanged_assets from the original public native task bundle; overlay each retained solution/solve.sh.',
        'manifest': 'independent/bundles/manifest.json',
    }
    (root / 'compact-evidence.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with tarfile.open(target, 'w:gz') as archive:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Linked evidence asset')
            if path.is_file() and path.relative_to(root).as_posix() not in omitted:
                archive.add(path, arcname='native/' + path.relative_to(root).as_posix(), recursive=False)
    return receipt


if __name__ == '__main__':
    pack(Path('/evidence/native'), Path('/work/native-evidence.tar.gz'))
