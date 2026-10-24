"""Remove owned archived/publicly reacquirable duplicates after hash gates."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import sha,write
from preserve import verified_receipt
from final_archive import DIRECTORY,verify


def stats(path):
    assert not path.is_symlink();files=[p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]
    assert not any(p.is_symlink() for p in files)
    return dict(files=len(files),logical_bytes=sum(p.stat().st_size for p in files))


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        value=json.loads(target.read_text());assert all(not (ROOT/r['path']).exists() for r in value['removed'])
        print(json.dumps(dict(already_completed=True,removed_logical_bytes=value['removed_logical_bytes'])));return
    manifest=verify(DIRECTORY);receipt=json.loads((DIRECTORY/'hf-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(DIRECTORY/'manifest.json')
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}=={'manifest.json':sha(DIRECTORY/'manifest.json'),**{r['path']:r['sha256'] for r in manifest['files']}}
    verified_receipt(ROOT/'private/harbor_comparison')
    assert json.loads((ROOT/'private/harbor_comparison/cleanup-proof.json').read_text())['cleanup']['verified_empty']
    for package in json.loads((ROOT/'package-acquisition.json').read_text())['packages']:
        assert sha(ROOT/'inputs-private'/package['filename'])==package['wheel_sha256']
        for row in package['source_files']:assert sha(ROOT/'inputs-private/source'/package['version']/row['path'])==row['sha256']
    pins=json.loads((ROOT/'control-pins.json').read_text());assert sha(ROOT/'inputs-private/tenacity-9.2.1-py3-none-any.whl')==pins['tenacity_wheel_sha256']
    names=['inputs-private/source','inputs-private/probe','inputs-private/harbor-0.6.6-py3-none-any.whl',
        'inputs-private/harbor-0.24.0-py3-none-any.whl','inputs-private/tenacity-9.2.1-py3-none-any.whl','private/final-summary-archive/tree']
    removed=[dict(path=name,**stats(ROOT/name)) for name in names if (ROOT/name).exists()]
    write(ROOT/'private/local-cleanup-intent.json',dict(removed=removed,verified_before_deletion=True,manifest_sha256=receipt['manifest_sha256']))
    for row in removed:
        path=ROOT/row['path']
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
    retained=[dict(path=name,reason=reason,**stats(ROOT/name)) for name,reason in [
        ('inputs-private/payloads','Immutable package/input/code payloads for inert completed invocation; no installed environments'),
        ('private/harbor_comparison','Canonical raw runtime and stage/HF evidence'),
        ('private/final-summary-archive','Canonical compact final source/summary archive')]]
    write(target,dict(issue=43,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=retained,
        cleanup_condition='Remove local canonical duplicates after review or verified rehydration, preserving cited HF snapshots',
        package_source_preservation='Pinned public wheel URLs/hashes and source-member identities retained; package binaries excluded from public archive',
        task_owned_tmp_paths=[],remote_cleanup_verified=True,verified_before_deletion=True,model_calls=0,other_tasks_or_credentials_touched=False))
    print(json.dumps(dict(removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=len(retained))))


if __name__=='__main__':main()
