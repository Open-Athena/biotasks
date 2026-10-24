"""Delete experiment-owned duplicates only after verified public preservation."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import inventory,sha,write
from preserve import verified_receipt
from preserve_final import verify as verify_final
from input_archive import verify as verify_inputs


def stats(path):
    files=[p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]
    assert not path.is_symlink() and not any(p.is_symlink() for p in files)
    return dict(files=len(files),logical_bytes=sum(p.stat().st_size for p in files))


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        value=json.loads(target.read_text());assert all(not (ROOT/r['path']).exists() for r in value['removed'])
        print(json.dumps(dict(already_completed=True,removed_logical_bytes=value['removed_logical_bytes'])));return
    final=verify_final();receipt=json.loads((ROOT/'final-evidence-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(ROOT/'final-evidence-manifest.json')
    expected={'manifest.json':sha(ROOT/'final-evidence-manifest.json'),**{r['path']:r['sha256'] for r in final['files']}}
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}==expected
    runtime=verified_receipt(ROOT/'private/OHIF__Viewers')
    source=verify_inputs(ROOT/'private/input-publication');source_receipt=json.loads((ROOT/'input-evidence-receipt.json').read_text())
    assert source_receipt['anonymous_download_verified'] and source_receipt['manifest_sha256']==sha(ROOT/'input-evidence-manifest.json')==sha(ROOT/'private/input-publication/manifest.json')
    assert {r['path'].removeprefix(source_receipt['prefix']+'/'):r['sha256'] for r in source_receipt['objects']}=={'manifest.json':sha(ROOT/'input-evidence-manifest.json'),**{r['path']:r['sha256'] for r in source['files']}}
    cohort=json.loads((ROOT/'cohort.json').read_text());prep=json.loads((ROOT/'candidate-preparation.json').read_text())
    assert sha(ROOT/'inputs-private/cold/inputs.tar.gz')==cohort['portable_input_bundle']['sha256']
    assert inventory(ROOT/'inputs-private/cold/tree')==cohort['portable_input_bundle']['files']
    assert inventory(ROOT/'inputs-private/portable/tree')==cohort['portable_input_bundle']['files']
    original=ROOT/'inputs-private/candidate/original/OHIF__Viewers'/prep['task']
    assert inventory(original)==prep['original_files']
    assert inventory(ROOT/'inputs-private/candidate/tree')==prep['task_bundle']['files']
    assert sha(ROOT/'inputs-private/candidate/tasks.tar.gz')==prep['task_bundle']['sha256']
    descriptor=json.loads((ROOT/'bootstrap-dependency.json').read_text())
    for name,key in [('docker_original.py','bootstrap/docker.py'),('runner_original.py','bootstrap/runner.py'),('auth_original.py','auth.py')]:assert sha(ROOT/'inputs-private/native-source'/name)==descriptor['native_source_sha256'][key]
    assert sha(ROOT/'inputs-private/recorded-actions.json')==descriptor['actions_sha256']
    assert sha(ROOT/'inputs-private/original-bootstrap.json')==descriptor['original_bootstrap_json_sha256']
    assert sha(ROOT/'inputs-private/native-baseline-task.tar.gz')=='784087ccf675d592e31d1012439777c4800548e8805ffa5878582c850eaa49a0'
    # Reviewed source/summary inputs are all represented in the final snapshot.
    review=json.loads((ROOT/'analysis/final-public-review.json').read_text());members={r['path']:r for r in final['files'][0]['members']}
    for row in review['inputs']:assert sha(ROOT/row['source'])==row['sha256']==members[row['path']]['sha256']
    names=['inputs-private/candidate','inputs-private/portable','inputs-private/cold','inputs-private/native-source',
        'inputs-private/recorded-actions.json','inputs-private/original-bootstrap.json','inputs-private/native-baseline-task.tar.gz','__pycache__','analysis/__pycache__']
    removed=[dict(path=n,**stats(ROOT/n)) for n in names if (ROOT/n).exists()]
    write(ROOT/'private/local-cleanup-intent.json',dict(paths=removed,final_manifest_sha256=receipt['manifest_sha256'],runtime_prefix=runtime['prefix'],portable_prefix=source_receipt['prefix'],verified_before_deletion=True))
    for row in removed:
        p=ROOT/row['path']
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
    retained=[]
    for name,reason in [('inputs-private/payloads','Immutable source-bound payloads for completed-controller reinvocation'),
        ('private/OHIF__Viewers','Canonical runtime archive and stage evidence'),('private/input-publication','Portable initializer archive and publication evidence'),
        ('private/final-snapshot','Canonical compact final summary/source snapshot')]:
        retained.append(dict(path=name,reason=reason,cleanup_condition='Remove local duplicates after review or verified rehydration; retain cited HF snapshot',**stats(ROOT/name)))
    write(target,dict(issue=39,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=retained,
        verified_before_deletion=True,task_owned_tmp_paths=[],remote_cleanup_already_verified=True,no_runtime_or_model_calls=True,
        credentials_or_other_tasks_touched=False,other_private_files='Small logs, drafts and publication intents retained until review; no transfer/readback cache retained'))
    print(json.dumps(dict(removed_logical_bytes=sum(r['logical_bytes'] for r in removed),removed_paths=[r['path'] for r in removed],model_calls=0)))


if __name__=='__main__':main()
