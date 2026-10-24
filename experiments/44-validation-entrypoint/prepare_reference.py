"""Restore reviewed notices anonymously; freeze two unchanged #38 references."""
from pathlib import Path

from biotasks.validation.archives import records
from biotasks.validation.files import read_json, sha, write_json
from biotasks.validation.preservation import inspect, transfer_limits

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[2] / '38/experiments/38-manifest-validation'


def main():
    from huggingface_hub import HfApi

    cohort = read_json(SOURCE/'cohort.json')
    policy = read_json(SOURCE/'public-policy.json')
    observed, exports, restored = [], [], []
    for family, name in [('opencobra__cobrapy','opencobra__cobrapy-1482'), ('scverse__scanpy','scverse__scanpy-4389')]:
        source = next(f for f in cohort['families'] if f['id']==family)
        original = next(t for t in source['tasks'] if t['task']==name)
        bundle = SOURCE/'inputs-private/payloads'/family/'tasks.tar.gz'
        assert sha(bundle)==source['task_bundle']['sha256']
        rows = records(bundle,'tar.gz')
        prefix = 'outputs/'+family+'/'+name+'/'
        selected = {n:r for n,r in rows.items() if n.startswith(prefix)}
        assert set(selected)=={r['path'] for r in original['files']}
        target = ROOT/'inputs-private'/family/name
        for spec in original['files']:
            row=selected[spec['path']]
            assert row['sha256']==spec['sha256'] and row['mode']==int(spec['mode'],8)
            path=target/spec['path'].removeprefix(prefix)
            if path.exists():assert sha(path)==row['sha256']
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(row['data']);path.chmod(row['mode'])
        receipt = read_json(SOURCE/'runs'/family/'hf-receipt.json')
        remote = next(r for r in receipt['objects'] if r['path'].endswith('/source/notices.tar.gz'))
        notice_archive = ROOT/'inputs-private'/family/'notices.tar.gz'
        notice_archive.parent.mkdir(parents=True,exist_ok=True)
        if not notice_archive.exists():
            with transfer_limits(ROOT):
                HfApi().download_bucket_files('open-athena/biotasks',[(remote['path'],notice_archive)],token=False,raise_on_missing_files=True)
        assert notice_archive.stat().st_size==remote['bytes'] and sha(notice_archive)==remote['sha256']==source['notices_bundle']['sha256']
        inspect(notice_archive.read_bytes(),'notices.tar.gz')
        restored.append(dict(family=family,remote=remote,anonymous_verified=True))
        notices=[]
        for name_in_archive,row in records(notice_archive,'tar.gz').items():
            path=ROOT/'inputs-private'/family/'notices'/name_in_archive
            if path.exists():assert sha(path)==row['sha256']
            else:
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['data'])
            notices.append(str(path.relative_to(ROOT)))
        baseline=read_json(SOURCE/'runs'/family/'readback.json')
        outcome=next((t for t in baseline.get('tasks',[]) if t['task']==name),None)
        observed.append(dict(repo=source['repo'],task=name,source_bundle_sha256=sha(bundle),notice_bundle_sha256=sha(notice_archive),source_files=original['files'],original_task_identity=original['original_task_identity'],native_inline_prepared_identity=original['prepared_task_identity'],eight_original_grading_assets_unchanged=True,expected_baseline=outcome if outcome else dict(stage=baseline['stage'],bootstrap_build_exit=baseline.get('bootstrap_build_exit')),source_review_sha256=policy['source_reviews'][family]))
        exports.append(dict(path=str(target.relative_to(ROOT)),initializer='native-inline',publication=dict(eligible=True,review='Reuse #38 public review '+policy['source_reviews'][family]+': unchanged eligible native-inline task/notices; isolated no-model logs and owned cleanup only. No images, environments, wheels, biological datasets or Matchms.'),notices=notices))
    write_json(ROOT/'reference-inputs.json',dict(schema_version=1,issue=44,pipeline_base='2a1950d239f1ada467c35393991dac87debe35f7',source_cohort_sha256=sha(SOURCE/'cohort.json'),source_policy_sha256=sha(SOURCE/'public-policy.json'),references=observed,notice_readbacks=restored,model_calls=0,task_repairs=0,scope='Infrastructure extraction; same native-inline assets as #38, no regeneration or bootstrap repair'))
    write_json(ROOT/'native-manifest.json',dict(schema_version=1,id='issue44-native',repo2rlenv_revision='27d04ee8203cd5b2f20c3997d13836e5f5b64238',backend=dict(type='iris',python='/home/exedev/projects/marin/.venv/bin/python',config='/home/exedev/projects/marin/lib/iris/config/marin.yaml',worker_revision='c7c14a252d',network='iris-egress',gcloud='/home/exedev/.local/google-cloud-sdk/bin/gcloud'),budget_ledger='../../../33/experiments/33-unattended-validation/budget.json',max_cpu_hours_per_task=6,archive=dict(kind='hf-public',bucket='open-athena/biotasks',prefix='research/44-validation-entrypoint'),exports=exports))
    print(dict(exports=len(exports),anonymous_notice_restores=len(restored),model_calls=0))


if __name__=='__main__':main()
