"""Delete owned duplicates only after exact public archive readback."""
import json
from pathlib import Path
import shutil
from common import sha,write
from preserve_source import DEST,ROOT,verify


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        value=json.loads(target.read_text());assert all(not (ROOT/r['path']).exists() for r in value['removed'])
        print(json.dumps(dict(already_completed=True,removed_bytes=value['removed_logical_bytes'])));return
    manifest=verify();receipt=json.loads((ROOT/'evidence-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(ROOT/'evidence-manifest.json')
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}=={'manifest.json':sha(ROOT/'evidence-manifest.json'),**{r['path']:r['sha256'] for r in manifest['files']}}
    review=json.loads((DEST/'snapshot/public-review.json').read_text())
    members={r['path']:r for r in manifest['files'][0]['members']}
    for row in review['inputs']:
        assert sha(ROOT/row['path'])==row['sha256']==members[row['path']]['sha256']
    package=json.loads((ROOT/'package-source-parity.json').read_text())['published']
    assert sha(ROOT/'inputs-private'/package['filename'])==package['wheel_sha256']
    names=['inputs-private','private/archive/tree'];removed=[]
    for name in names:
        path=ROOT/name;files=[p for p in path.rglob('*') if p.is_file()]
        assert not path.is_symlink() and not any(p.is_symlink() for p in files)
        removed.append(dict(path=name,files=len(files),logical_bytes=sum(p.stat().st_size for p in files)))
    write(ROOT/'private/local-cleanup-intent.json',dict(removed=removed,manifest_sha256=receipt['manifest_sha256'],verified_before_deletion=True))
    for name in names:shutil.rmtree(ROOT/name)
    write(target,dict(issue=42,verified_before_deletion=True,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),
        retained=[dict(path='private/archive/snapshot',reason='Canonical compact reviewed source/notices snapshot; remove local duplicate after review or verified rehydration while retaining cited HF archive')],
        package_binary_preservation='Excluded deliberately; pinned public acquisition URL/hash retained in package-source-parity.json',
        task_owned_tmp_paths=[],remote_resources_created=False,upstream_installed_or_executed=False,model_calls=0,other_sessions_touched=False))
    print(json.dumps(dict(removed_logical_bytes=sum(r['logical_bytes'] for r in removed),tmp_paths=[])))


if __name__=='__main__':main()
