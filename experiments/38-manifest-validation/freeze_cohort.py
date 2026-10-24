"""Freeze data descriptors and packages; no scheduler or model operations."""
import json
from pathlib import Path
import shutil
import tomllib

from common import UPSTREAM,archive_tree,content_sha,inventory,native_prefix,run_name,sha,task_identity,write
from evidence import verify_imported_failure

ROOT=Path(__file__).resolve().parent


def notices(family,originals,destination):
    manifest=json.loads(Path(family['source_manifest']).read_text())
    baseline=Path(family['source_manifest']).parents[2]
    refs={t[k] for t in originals for k in ['base_commit','head_commit']}
    wanted=['source-notices/'+family['slug']+'--LICENSE']+[
        'source-notices/history/'+family['slug']+'/'+ref+'--LICENSE' for ref in sorted(refs)]
    for name in wanted:
        row=next(r for r in manifest['files'] if r['path']==name)
        if '/history/' in name:path=baseline/'history-wide/source-notices'/name.removeprefix('source-notices/history/')
        else:path=baseline/'preflight/licenses'/name.removeprefix('source-notices/')
        assert sha(path)==row['sha256']
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    upstream=baseline/'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
    assert sha(upstream)=='c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'
    shutil.copyfile(upstream,destination/'source-notices/Repo2RLEnv-LICENSE')


def exclusions():
    tree=ROOT.parents[2]
    references=[tree/'37/experiments/37-ohif-inline-runtime/inputs-private/original-workers.json']
    existing=json.loads(references[0].read_text())
    rows=[dict(job_id=r['job_id'],worker_id=w,receipt_sha256=r.get('receipt_sha256'))
        for r in existing['jobs'] for w in r['worker_ids']]
    checkpoint=Path('/home/exedev/.local/share/biotasks/checkpoints/issue28-history-wide-20261022')
    paths=[checkpoint/'biotasks28-history-opencobra-cobrapy-001-receipt.json',
        checkpoint/'biotasks28-history-scverse-scanpy-001-receipt.json',
        tree/'37/experiments/37-ohif-inline-runtime/run-private/biotasks37-ohif-5996-inline-001/submission.json']
    for path in paths:
        data=json.loads(path.read_text());assert data['worker_id'] and data['job_id']
        rows.append(dict(job_id=data['job_id'],worker_id=data['worker_id'],receipt_sha256=sha(path)))
    workers=sorted({r['worker_id'] for r in rows})
    return dict(excluded_worker_ids=workers,excluded_worker_prefixes=sorted({w.rsplit('-worker-',1)[0] for w in workers}),
        sources=rows,provenance='Retained acknowledged receipts; not fresh status observations')


def main():
    plan=json.loads((ROOT/'source-plan.json').read_text());acquisition=json.loads((ROOT/'acquisition.json').read_text())
    preparation=json.loads((ROOT/'native-preparation.json').read_text())
    assert preparation['upstream_revision']==UPSTREAM and preparation['model_calls']==preparation['docker_commands']==0
    assert acquisition['source_plan_sha256']==sha(ROOT/'source-plan.json')
    frozen=ROOT/'inputs-private/frozen';assert not frozen.exists();frozen.mkdir(mode=0o700,parents=True)
    family_specs=[]
    for family in plan['families']:
        acquired=next(r for r in acquisition['families'] if r['repo']==family['repo'])
        prepared=Path(acquired['acquired_root'])/'prepared'
        recorded=next(r for r in preparation['families'] if r['repo']==family['repo'])['prepared_inventory']
        assert inventory(prepared)==recorded
        directory=frozen/family['slug'];directory.mkdir()
        tree=directory/'tree';root=tree/'outputs'/family['slug'];root.mkdir(parents=True)
        tasks=[];prefixes={};refs=set()
        for original in acquired['tasks']:
            task=original['task'];source=prepared/task;rows=inventory(source)
            assert len(rows)==10
            if family['mode']=='native_inline':
                assert task_identity(family['repo'],task,inventory(Path(acquired['acquired_root'])/'original'/task))==original['task_content_identity_sha256']
            mapped={r['path']:r for r in rows};unchanged=0
            for old in original['original_task_files']:
                if old['path'] in ('environment/Dockerfile','task.toml'):continue
                new=mapped[old['path']]
                assert new['sha256']==old['sha256'] and new['bytes']==old['bytes'] and int(new['mode'],8)==old['mode']
                unchanged+=1
            assert unchanged==8
            config=tomllib.loads((source/'task.toml').read_text());assert config['verifier']['timeout_sec']==300
            prefix,base=native_prefix((source/'environment/Dockerfile').read_bytes());prefixes[content_sha(prefix)]=(prefix,base)
            for attempt in original['attempts']:
                if attempt.get('bootstrap_image_id'):refs.add(attempt['bootstrap_image_id'])
                refs.update(attempt.get('runtime_image_ids',[]))
            shutil.copytree(source,root/task)
            files=[dict(r,path='outputs/'+family['slug']+'/'+task+'/'+r['path']) for r in rows]
            tasks.append(dict(task=task,base_commit=original['base_commit'],head_commit=original['head_commit'],
                original_task_identity=original['task_content_identity_sha256'],prepared_task_identity=task_identity(family['repo'],task,rows),
                original_grading_assets_unchanged=8,files=files,
                expected_f2p=len(json.loads((source/'tests/f2p.json').read_text())),
                expected_p2p=len(json.loads((source/'tests/p2p.json').read_text()))))
        assert len(prefixes)==1
        prefix_sha,(prefix,base)=next(iter(prefixes.items()));(directory/'bootstrap-prefix.Dockerfile').write_bytes(prefix)
        if acquired['cache_path']:
            cache=json.loads((Path(acquired['acquired_root'])/acquired['cache_path']).read_text());refs.add(cache['image_tag'])
        bundle=archive_tree(tree,directory/'tasks.tar.gz');bundle['path']=str(Path(bundle['path']).relative_to(ROOT))
        source_notices=directory/'notices';source_notices.mkdir();notices(family,acquired['tasks'],source_notices)
        notice_bundle=archive_tree(source_notices,directory/'notices.tar.gz');notice_bundle['path']=str(Path(notice_bundle['path']).relative_to(ROOT))
        control_plan=dict(repositories=[dict(repo=family['repo'],slug=family['slug'],tasks=[dict(task=t['task'],
            original_files=t['files'],proposed_arms_seconds=[300]) for t in tasks])],model_calls=0,task_repairs=0)
        hours=family['maximum_cpu_hours'];resources=dict(plan['resources'])
        resources.update(maximum_cpu_hours=hours,timeout_seconds=int(hours*3600/resources['cpus'])-600 if hours else 0)
        resources['work_deadline_seconds']=resources['timeout_seconds']-600 if hours else 0
        item=dict(id=family['slug'],repo=family['repo'],mode=family['mode'],tasks=tasks,task_bundle=bundle,
            notices_bundle=notice_bundle,control_plan=control_plan,public_base_ref=base,
            bootstrap_prefix_sha256=prefix_sha,bootstrap_prefix_file=str((directory/'bootstrap-prefix.Dockerfile').relative_to(ROOT)),
            original_image_refs=sorted(r for r in refs if r),resources=resources,
            provenance=acquired['provenance'],public_review_sha256=acquired['public_review_sha256'])
        if family['mode']=='reference_stop':
            item['imported_failure']=verify_imported_failure(ROOT/'inputs-private/acquired/failure-reference',prepared)
            assert item['imported_failure']['bootstrap_prefix_sha256']==prefix_sha
            item['status']='not_attempted_shared_prerequisite_stop'
        else:item['status']='ready_for_admission'
        family_specs.append(item)
    assert sum(len(f['tasks']) for f in family_specs)==plan['expected_public_tasks']
    cohort=dict(schema_version=1,issue=38,upstream_revision=UPSTREAM,source_plan_sha256=sha(ROOT/'source-plan.json'),
        source_ledger_sha256=acquisition['source_ledger_sha256'],families=family_specs,exclusions=exclusions(),
        model_calls_enabled=False,new_capacity_allowed=False,original_cohort_tasks=83,public_tasks=25,
        restricted_tasks_excluded=58,original_grading_assets_unchanged=25*8,
        historical_control_totals_unchanged=True,epic_cpu_ceiling=32,operating_ceiling_usd=90)
    write(ROOT/'cohort.json',cohort)
    print(json.dumps(dict(public_tasks=25,families=len(family_specs),runtime_families=sum(f['mode']=='native_inline' for f in family_specs),
        imported_stop_tasks=sum(len(f['tasks']) for f in family_specs if f['mode']=='reference_stop'),model_calls=0)))


if __name__=='__main__':main()
