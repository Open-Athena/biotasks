"""Hash-bound public acquisition, then separate audited native metadata preparation."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
import tomllib

from common import UPSTREAM,archive_tree,content_sha,family_key,inventory,json_sha,native_prefix,run_name,safe,sha,task_identity,write

ROOT=Path(__file__).resolve().parent


def staged_object(manifest_path,receipt_path,staging,name):
    manifest=json.loads(Path(manifest_path).read_text());receipt=json.loads(Path(receipt_path).read_text())
    assert receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(manifest_path)
    row=next(r for r in manifest['files'] if r['path']==name)
    record=next(r for r in receipt['objects'] if r['path']==receipt['prefix']+'/'+name)
    assert record['sha256']==row['sha256'] and record['bytes']==row['bytes']
    source=Path(staging)/safe(name)
    assert source.is_file() and not source.is_symlink() and source.stat().st_size==row['bytes'] and sha(source)==row['sha256']
    return source,row


def acquire(plan):
    target=ROOT/'inputs-private/acquired'
    assert not target.exists(), 'Never overwrite acquired inputs'
    target.mkdir(parents=True,mode=0o700)
    ledger=json.loads(Path(plan['source_ledger']).read_text())
    assert len(ledger['tasks'])==plan['original_cohort_tasks']
    assert sum(f['expected_tasks'] for f in plan['families'])==plan['expected_public_tasks']
    assert plan['original_cohort_tasks']-plan['expected_public_tasks']==plan['restricted_tasks_excluded']
    profile=json.loads((ROOT/'archive-client-profile.json').read_text());os.environ.update(profile['environment'])
    downloaded=0;records=[]
    with tempfile.TemporaryDirectory(prefix='source-download-',dir=ROOT/'inputs-private') as td:
        os.environ['HF_XET_CACHE']=str(Path(td)/'xet')
        from huggingface_hub import HfApi
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars();api=HfApi(token=False)
        for family in plan['families']:
            repo=family['repo'];slug=family['slug'];assert family_key(repo)==slug
            tasks=sorted([t for t in ledger['tasks'] if t['repo']==repo],key=lambda t:int(t['task'].rsplit('-',1)[1]))
            assert len(tasks)==family['expected_tasks']
            review=json.loads(Path(family['public_review']).read_text());assert review['public_eligible'] and review['repo']==repo
            base=target/slug;base.mkdir()
            if family['mode']=='reference_stop':
                source,row=staged_object(plan['candidate_manifest'],plan['candidate_receipt'],plan['candidate_staging'],'evidence/candidate-tasks.tar.gz')
                expected={f"outputs/{slug}/{t['task']}/{f['path']}":f for t in tasks for f in t['original_task_files']}
                extracted=set()
                with tarfile.open(source) as tar:
                    for member in tar:
                        safe(member.name);assert member.isfile() and member.name in expected and member.name not in extracted
                        extracted.add(member.name);raw=tar.extractfile(member).read()
                        assert len(raw)==member.size<1024**2
                        name=member.name.removeprefix('outputs/'+slug+'/')
                        path=base/'prepared'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(member.mode)
                        original=expected[member.name]
                        if not name.endswith(('/environment/Dockerfile','/task.toml')):
                            assert content_sha(raw)==original['sha256'] and member.mode==original['mode']
                assert extracted==set(expected)
                source_provenance=dict(kind='sealed lookup-only candidate',archive_sha256=row['sha256'],public_receipt_sha256=sha(plan['candidate_receipt']))
                cache=None
            else:
                assert family['mode']=='native_inline'
                manifest=json.loads(Path(family['source_manifest']).read_text())
                phase=next(r for r in manifest['files'] if r['path']=='evidence/phase-artifacts.tar.gz')
                assert phase['bytes']<16*1024**2
                archive=Path(td)/(slug+'.tar.gz')
                remote='research/28-catalogued-fields/'+manifest['created_utc'][:10]+'/'+sha(family['source_manifest'])+'/'+phase['path']
                api.download_bucket_files('open-athena/biotasks',[(remote,archive)],raise_on_missing_files=True,token=False)
                assert archive.stat().st_size==phase['bytes'] and sha(archive)==phase['sha256']
                downloaded+=phase['bytes'];assert downloaded<32*1024**2
                expected={f"outputs/{slug}/{t['task']}/{f['path']}":f for t in tasks for f in t['original_task_files']}
                member_specs={r['path']:r for r in phase['members']};seen=set();caches=[];total=0
                with tarfile.open(archive,'r|gz') as tar:
                    for member in tar:
                        safe(member.name);total+=member.size;assert total<256*1024**2
                        is_cache=member.name.startswith('bootstrap/') and member.name.endswith('/bootstrap.json')
                        if member.name not in expected and not is_cache:continue
                        assert member.isfile() and member.name not in seen and member.size<1024**2
                        seen.add(member.name);raw=tar.extractfile(member).read();spec=member_specs[member.name]
                        assert content_sha(raw)==spec['sha256'] and len(raw)==spec['bytes']
                        if is_cache:
                            path=base/'workspace'/member.name;caches.append(str(path.relative_to(base)))
                        else:
                            name=member.name.removeprefix('outputs/'+slug+'/');path=base/'original'/name
                            assert content_sha(raw)==expected[member.name]['sha256']
                        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(member.mode)
                assert set(expected)<=seen and len(caches)==1;cache=caches[0]
                archive.unlink()
                source_provenance=dict(kind='original public phase',archive_sha256=phase['sha256'],source_manifest_sha256=sha(family['source_manifest']),object_path=remote)
            records.append(dict(repo=repo,slug=slug,mode=family['mode'],tasks=tasks,cache_path=cache,
                acquired_root=str(base),provenance=source_provenance,public_review_sha256=sha(family['public_review'])))
    # Import the measured failure bytes, not merely a boolean in an old report.
    failure_dir=target/'failure-reference';failure_dir.mkdir()
    for name in ['evidence/runtime.tar.zst','evidence/native-task.tar.gz','provenance/runtime-readback.json']:
        path,row=staged_object(plan['failure_manifest'],plan['failure_receipt'],plan['failure_staging'],name)
        dest=failure_dir/Path(name).name;shutil.copyfile(path,dest)
    write(ROOT/'acquisition.json',dict(source_plan_sha256=sha(ROOT/'source-plan.json'),source_ledger_sha256=sha(plan['source_ledger']),
        families=records,downloaded_bytes=downloaded,download_and_xet_cache_removed=True,model_calls=0,restricted_tasks_acquired=0))
    print(json.dumps(dict(acquired_tasks=sum(len(r['tasks']) for r in records),downloaded_bytes=downloaded,model_calls=0)))


def grading_contract(data):
    data=deepcopy(data);meta=data.get('metadata',{}).get('repo2env',{})
    meta.pop('reproducibility',None);meta.pop('spec_version',None)
    return data


def native_prepare(plan):
    acquisition=json.loads((ROOT/'acquisition.json').read_text())
    assert acquisition['source_plan_sha256']==sha(ROOT/'source-plan.json')
    source=Path(plan['upstream_package']);source_manifest=json.loads(Path(plan['upstream_acquisition']).read_text())
    assert source_manifest['revision']==UPSTREAM
    for row in source_manifest['files']:assert sha(source/row['path'])==row['sha256']
    blocked=[]
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            blocked.append(event);raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            path=str(Path(args[0]).resolve())
            if any(part in path for part in ('.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json')):
                blocked.append('credential_store_open');raise AssertionError('Credential read')
    sys.addaudithook(audit)
    sys.path[:0]=[str(source/'src'),plan['upstream_extra_modules']]
    from repo2rlenv.registry import integration as native
    assert Path(native.__file__).resolve()==source/'src/repo2rlenv/registry/integration.py'
    results=[];cwd=Path.cwd()
    for family in acquisition['families']:
        base=Path(family['acquired_root'])
        if family['mode']=='native_inline':
            assert not (base/'prepared').exists();shutil.copytree(base/'original',base/'prepared')
            os.chdir(base)
            try:result=native.prepare_dataset_for_push(base/'prepared',hf_owner='open-athena',inline_dockerfile=True,pushed_by='biotasks-issue38')
            finally:os.chdir(cwd)
            assert result.tasks_rewritten==len(family['tasks'])
            changed=[]
            for task in family['tasks']:
                name=task['task'];old=inventory(base/'original'/name);new=inventory(base/'prepared'/name)
                assert {r['path'] for r in old}=={r['path'] for r in new}
                difference=[a['path'] for a,b in zip(old,new) if a!=b]
                assert set(difference)<= {'environment/Dockerfile','task.toml'}
                assert grading_contract(tomllib.loads((base/'original'/name/'task.toml').read_text()))==grading_contract(tomllib.loads((base/'prepared'/name/'task.toml').read_text()))
                changed.extend(name+'/'+p for p in difference)
            outcome=asdict(result)
        else:changed=[];outcome=dict(mode='imported lookup-only candidate',source=family['provenance'])
        results.append(dict(repo=family['repo'],mode=family['mode'],tasks=len(family['tasks']),native_result=outcome,
            changed_files=changed,prepared_inventory=inventory(base/'prepared')))
    assert not blocked
    write(ROOT/'native-preparation.json',dict(upstream_revision=UPSTREAM,source_modified=False,full_native_api_executed=True,
        families=results,blocked_operations=blocked,model_calls=0,docker_commands=0,credential_store_reads=0))
    print(json.dumps(dict(native_prepared_tasks=sum(f['tasks'] for f in results if f['mode']=='native_inline'),
        imported_candidate_tasks=sum(f['tasks'] for f in results if f['mode']=='reference_stop'),model_calls=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['acquire','native'])
    args=parser.parse_args();plan=json.loads((ROOT/'source-plan.json').read_text())
    assert plan['upstream_revision']==UPSTREAM and not plan['model_calls_enabled'] and not plan['new_capacity_allowed']
    acquire(plan) if args.action=='acquire' else native_prepare(plan)
