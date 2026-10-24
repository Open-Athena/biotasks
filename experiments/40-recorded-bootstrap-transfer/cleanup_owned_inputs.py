"""Remove only this source assessment's verified redundant working copies."""
import json
from pathlib import Path
import shutil

from common import sha,write
from preserve_evidence import ROOT,verify


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        value=json.loads(target.read_text());assert all(not (ROOT/r['path']).exists() for r in value['removed'])
        print(json.dumps(dict(already_completed=True,removed_logical_bytes=value['removed_logical_bytes'])));return
    manifest=verify();receipt=json.loads((ROOT/'assessment-evidence-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(ROOT/'assessment-evidence-manifest.json')
    expected={'manifest.json':sha(ROOT/'assessment-evidence-manifest.json'),**{r['path']:r['sha256'] for r in manifest['files']}}
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}==expected
    acquisition=json.loads((ROOT/'acquisition.json').read_text());assert acquisition['anonymous_download_verified'] and acquisition['transfer_cache_removed']
    for row in acquisition['files']:assert sha(ROOT/row['path'])==row['sha256']
    review=json.loads((ROOT/'public-review.json').read_text())
    archived={r['path']:r for r in manifest['files'][0]['members']}
    for row in review['inputs']:assert sha(ROOT/row['source'])==row['sha256']==archived[row['path']]['sha256']
    paths=['inputs-private/acquired','inputs-private/derived','__pycache__'];removed=[]
    for name in paths:
        path=ROOT/name
        if not path.exists():continue
        assert path.is_dir() and not path.is_symlink()
        files=[p for p in path.rglob('*') if p.is_file()];assert not any(p.is_symlink() for p in path.rglob('*'))
        removed.append(dict(path=name,files=len(files),logical_bytes=sum(p.stat().st_size for p in files)))
    write(ROOT/'private/cleanup-intent.json',dict(paths=removed,verified_manifest_sha256=receipt['manifest_sha256'],source_anonymous_readback_verified=True))
    for row in removed:shutil.rmtree(ROOT/row['path'])
    inputs=ROOT/'inputs-private'
    if inputs.exists() and not any(inputs.iterdir()):inputs.rmdir()
    assert not (ROOT/'private/transfer-cache').exists() and not list((ROOT/'private').glob('anonymous-readback-*'))
    value=dict(issue=40,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),
        retained=[dict(path='private/assessment-snapshot',reason='Canonical reviewed metadata/action/notice snapshot',cleanup_condition='Remove local staging after review or verified rehydration; retain cited HF prefix')],
        hf_prefix=receipt['prefix'],raw_originals_unchanged=True,raw_source_archives_remain_at_acquisition_references=True,
        task_owned_tmp_paths=[],new_remote_jobs=0,new_model_calls=0,credentials_or_other_tasks_touched=False)
    assert all(not (ROOT/r['path']).exists() for r in removed)
    write(target,value);print(json.dumps(dict(removed_logical_bytes=value['removed_logical_bytes'],new_remote_jobs=0,new_model_calls=0)))


if __name__=='__main__':main()
