"""Remove only verified redundant inputs owned by this experiment."""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import inventory,sha,write
from preserve import verified_receipt
from preserve_final import verify as verify_final
from prepare_inputs import staged_object


def stats(path):
    files=[p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]
    assert not path.is_symlink() and not any(p.is_symlink() for p in files)
    return dict(files=len(files),logical_bytes=sum(p.stat().st_size for p in files))


def main():
    target=ROOT/'local-cleanup.json'
    if target.exists():
        prior=json.loads(target.read_text())
        assert all(not (ROOT/r['path']).exists() for r in prior['removed'])
        print(json.dumps(dict(already_completed=True,removed_logical_bytes=prior['removed_logical_bytes'])));return
    m=verify_final();receipt=json.loads((ROOT/'final-evidence-receipt.json').read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(ROOT/'final-evidence-manifest.json')
    expected={'manifest.json':sha(ROOT/'final-evidence-manifest.json'),**{r['path']:r['sha256'] for r in m['files']}}
    assert {r['path'].removeprefix(receipt['prefix']+'/'):r['sha256'] for r in receipt['objects']}==expected
    cohort=json.loads((ROOT/'cohort.json').read_text());plan=json.loads((ROOT/'source-plan.json').read_text())
    acquisition=json.loads((ROOT/'acquisition.json').read_text())
    preparation=json.loads((ROOT/'native-preparation.json').read_text())
    for family in acquisition['families']:
        base=Path(family['acquired_root'])
        expected=next(f['prepared_inventory'] for f in preparation['families'] if f['repo']==family['repo'])
        assert inventory(base/'prepared')==expected
        if family['mode']=='native_inline':
            rows={t['task']+'/'+f['path']:dict(bytes=f['bytes'],mode=format(f['mode'],'o'),sha256=f['sha256'])
                for t in family['tasks'] for f in t['original_task_files']}
            assert {f['path']:{k:v for k,v in f.items() if k!='path'} for f in inventory(base/'original')}==rows
    for family in cohort['families']:
        frozen=ROOT/'inputs-private/frozen'/family['id']
        assert inventory(frozen/'tree')==family['task_bundle']['files']
        assert inventory(frozen/'notices')==family['notices_bundle']['files']
        assert sha(frozen/'bootstrap-prefix.Dockerfile')==family['bootstrap_prefix_sha256']
        if family['mode']=='native_inline':
            d=ROOT/'private'/family['id'];verified_receipt(d)
            for key,name in [('task_bundle','native-tasks.tar.gz'),('notices_bundle','notices.tar.gz')]:
                assert sha(ROOT/family[key]['path'])==family[key]['sha256']==sha(d/'snapshot/source'/name)
        else:
            canonical,row=staged_object(plan['candidate_manifest'],plan['candidate_receipt'],plan['candidate_staging'],'evidence/candidate-tasks.tar.gz')
            assert sha(ROOT/family['task_bundle']['path'])==sha(canonical)==row['sha256']
    review=json.loads((ROOT/'analysis/final-public-review.json').read_text())
    members={r['path']:r for r in m['files'][0]['members']}
    for row in review['inputs']:
        assert members[row['path']]['sha256']==row['sha256']
        assert sha(ROOT/row['source'])==row['sha256']
    # These exact directories were created by this task; never touch another branch/cache.
    names=['inputs-private/acquired','inputs-private/frozen','private/pre-submission-attempt-1','__pycache__','analysis/__pycache__']
    removed=[]
    for name in names:
        path=ROOT/name
        if path.exists():removed.append(dict(path=name,**stats(path)))
    intent=dict(scope='Exact experiment-owned redundant working copies only',paths=removed,
        final_verified_manifest_sha256=receipt['manifest_sha256'],native_snapshots_verified=True,
        lookup_candidate_snapshot_verified=True,credentials_or_other_tasks_touched=False)
    write(ROOT/'private/local-cleanup-intent.json',intent)
    for row in removed:shutil.rmtree(ROOT/row['path'])
    retained=[]
    for name,reason,condition in [
        ('inputs-private/payloads','Immutable compiled payloads needed for completed-controller reinvocation','Remove after review/related #39 work or verified rehydration procedure'),
        ('private/opencobra__cobrapy','Canonical snapshot, output archive and stage evidence for readback/reinvocation','Remove redundant local copies after review; retain cited HF snapshot'),
        ('private/scverse__scanpy','Canonical negative-build snapshot and stage evidence','Remove redundant local copies after review; retain cited HF snapshot'),
        ('private/final-snapshot','Verified compact final summary/source archive','Remove local staging after review; retain cited HF snapshot')]:
        retained.append(dict(path=name,reason=reason,cleanup_condition=condition,**stats(ROOT/name)))
    result=dict(issue=38,removed=removed,removed_logical_bytes=sum(r['logical_bytes'] for r in removed),retained=retained,
        final_hf_prefix=receipt['prefix'],verified_before_deletion=True,task_owned_tmp_paths=[],
        immutable_payloads_and_stage_evidence_retained=True,remote_cleanup_already_verified=True,
        no_runtime_or_model_calls=True,credentials_or_other_tasks_touched=False,
        other_private_files='Small watcher logs, publication drafts/intents and receipt-schema failure metadata remain until review; no transfer/readback cache retained')
    assert not (ROOT/'private/final-transfer-cache').exists()
    assert not list((ROOT/'private').glob('final-anonymous-readback-*'))
    assert all(not (ROOT/r['path']).exists() for r in removed)
    write(target,result);print(json.dumps(dict(removed_logical_bytes=result['removed_logical_bytes'],removed_paths=[r['path'] for r in removed],model_calls=0)))


if __name__=='__main__':main()
