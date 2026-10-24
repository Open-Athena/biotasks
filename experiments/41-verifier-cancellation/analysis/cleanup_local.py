"""Remove owned, archived or publicly reacquirable duplicates after verification."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import sha,write
import preserve
from finalize import DIRECTORY,verify
from preserve_failed import DEST,verify as verify_failed


def receipt_matches(directory,manifest):
    receipt=json.loads((directory/'hf-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(directory/'manifest.json')
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}=={'manifest.json':sha(directory/'manifest.json'),**{r['path']:r['sha256'] for r in manifest['files']}}
    return receipt


def stats(path):
    assert not path.is_symlink()
    files=[p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]
    assert not any(p.is_symlink() for p in files)
    return dict(files=len(files),logical_bytes=sum(p.stat().st_size for p in files))


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        record=json.loads(target.read_text());assert all(not (ROOT/r['path']).exists() for r in record['removed'])
        print(json.dumps(dict(already_completed=True,removed_logical_bytes=record['removed_logical_bytes'])));return
    final=verify(DIRECTORY);receipt_matches(DIRECTORY,final)
    receipt_matches(DEST,verify_failed(DEST))
    preserve.verified_receipt(ROOT/'private/harbor_timeout')
    # Earlier completed native infrastructure failure was archived before rerendering.
    old=ROOT/'private/compose-failure-1/harbor_timeout'
    old_manifest=json.loads((old/'manifest.json').read_text())
    receipt_matches(old,old_manifest)
    assert json.loads((old/'cleanup-proof.json').read_text())['cleanup']['verified_empty']
    complete=json.loads((ROOT/'private/harbor_timeout/complete.json').read_text())
    assert complete['model_calls']==0
    for acq_name,directory in [('package-acquisition.json','inputs-private/source'),('test-dependency-acquisition.json','inputs-private/check-dependency/source')]:
        acq=json.loads((ROOT/acq_name).read_text())
        for row in acq['source_files']:assert sha(ROOT/directory/row['path'])==row['sha256']
    # Fixture bundles and all source/configuration are in verified runtime/final snapshots.
    # Public package binaries are intentionally excluded: their pinned URLs/hashes survive.
    names=['inputs-private/source','inputs-private/check-dependency','inputs-private/harbor-0.6.6-py3-none-any.whl',
        'inputs-private/probe','private/failed-attempt-1','private/compose-failure-1','private/failed-startup-archive/tree','private/final-summary-archive/tree']
    removed=[dict(path=name,**stats(ROOT/name)) for name in names if (ROOT/name).exists()]
    write(ROOT/'private/local-cleanup-intent.json',dict(removed=removed,verified_before_deletion=True,final_manifest_sha256=sha(DIRECTORY/'manifest.json')))
    for row in removed:
        path=ROOT/row['path']
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
    retained=[dict(path=name,reason=reason,**stats(ROOT/name)) for name,reason in [
        ('inputs-private/payloads','Exact immutable payloads needed for inert completed-controller reinvocation; wheels are public packages, not installed environments.'),
        ('private/harbor_timeout','Canonical runtime archive, snapshot and journal evidence.'),
        ('private/failed-startup-archive','Canonical failed-startup snapshot and publication evidence.'),
        ('private/final-summary-archive','Canonical final summary snapshot and publication evidence.')]]
    write(target,dict(issue=41,verified_before_deletion=True,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=retained,
        cleanup_condition='Retain cited HF evidence; remove remaining local canonical copies after review or verified rehydration.',
        task_owned_tmp_paths=[],remote_cleanup_already_verified=True,model_calls=0,other_sessions_or_credentials_touched=False))
    print(json.dumps(dict(removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=len(retained))))


if __name__=='__main__':main()
