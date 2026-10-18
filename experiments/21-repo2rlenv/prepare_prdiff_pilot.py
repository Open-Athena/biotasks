"""Freeze three native similarity tasks per repository; preserve original assets."""
import argparse
import datetime
import hashlib
import json
import tarfile
import tomllib
from pathlib import Path
from prdiff_runtime_input import TOOLING_APPEND,NETWORK_APPEND,check_task

ROOT=Path(__file__).resolve().parent
SELECTED={
 'biopython':['biopython__biopython-5338','biopython__biopython-5369','biopython__biopython-5376'],
 'skbio':['scikit-bio__scikit-bio-2630','scikit-bio__scikit-bio-2633','scikit-bio__scikit-bio-2636'],
 'bedtools':['arq5x__bedtools2-1030','arq5x__bedtools2-1043','arq5x__bedtools2-999'],
 'deseq':['thelovelab__DESeq2-118','thelovelab__DESeq2-59','thelovelab__DESeq2-64'],
}


def prepare(destination):
    archive=ROOT/'evidence/pr-diff-01/generated-bundles.tar.gz'
    with archive.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()=='dcbf43f02a2a69014612a25341e1208c6fd881231f55d4c4404083b32e312841'
    checks={x['task']:x for x in json.loads((ROOT/'evidence/pr-diff-01/patch-application.json').read_text())['tasks']}
    diagnostics={x['task']:x for x in json.loads((ROOT/'evidence/pr-diff-01/scorer-diagnostics.json').read_text())['tasks']}
    names={name for cohort in SELECTED.values() for name in cohort};assets={name:{} for name in names}
    destination.mkdir(exist_ok=False)
    with tarfile.open(archive,'r|gz') as source:
        for member in source:
            rel=Path(member.name)
            if len(rel.parts)<4 or rel.parts[2] not in names:continue
            name=rel.parts[2];asset=Path(*rel.parts[3:])
            if member.isdir():continue
            assert member.isfile() and not asset.is_absolute() and '..' not in asset.parts
            assert member.size<=512*1024
            data=source.extractfile(member).read();target=destination/'tasks'/name/asset
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(member.mode & 0o7777)
            assets[name][str(asset)]={'sha256':hashlib.sha256(data).hexdigest(),'mode':member.mode & 0o7777}
    cohorts=[]
    for cohort,names in SELECTED.items():
        items=[]
        for name in names:
            task=destination/'tasks'/name;meta=tomllib.loads((task/'task.toml').read_text())['metadata']['repo2env']
            assert meta['pipeline']=='pr_diff' and meta['reward_kinds']==['diff_similarity']
            assert checks[name]['status']=='patch_applies' and checks[name]['base']==meta['ref']
            assert diagnostics[name]['scores']['oracle']['reward']==1 and diagnostics[name]['scores']['empty']['reward']==0
            parent='repo2rlenv-pr-diff/'+meta['content_hash'].split(':')[1]
            original={k:v['sha256'] for k,v in assets[name].items()};modes={k:v['mode'] for k,v in assets[name].items()}
            docker=task/'environment/Dockerfile';docker.write_bytes(docker.read_bytes()+TOOLING_APPEND.encode());docker.chmod(modes['environment/Dockerfile'])
            config=task/'task.toml';config.write_bytes(config.read_bytes()+NETWORK_APPEND.encode());config.chmod(modes['task.toml'])
            runtime={str(f.relative_to(task)):hashlib.sha256(f.read_bytes()).hexdigest() for f in task.rglob('*') if f.is_file()}
            review={'stage':'prepared_for_native_runtime_controls','status':'runtime_validation_pending','task':name,'task_id':parent,
                    'repository':meta['repo'],'base':meta['ref'],'source_reference':meta['reference'],
                    'native_reward_kind':'diff_similarity','reward':{'kind':'native_patch_similarity','range':[0,1]},
                    'asset_sha256':original,'runtime_asset_sha256':runtime,'asset_modes':modes,
                    'independent_pure_controls':diagnostics[name]['scores'],'patch_application':checks[name]['status'],
                    'limitations':['Native score measures oracle-patch similarity, not functional correctness or biological inference.','Reference patch application was checked on exact base text files; runtime controls remain pending.','Native weights can award substantial structural credit to reversed changes; no pass/fail interpretation.','Biopython selection includes documentation; scikit-bio GPU-dispatch task does not execute or validate a GPU.']}
            folder=destination/'reviews';folder.mkdir(exist_ok=True);review_path=folder/(name+'.json');review_path.write_text(json.dumps(review,indent=2)+'\n')
            runtime_path=folder/(name+'-runtime.json');runtime_path.write_text(json.dumps({'task_id':parent,'changed_assets':['environment/Dockerfile','task.toml'],'asset_sha256':runtime,'dockerfile_append':TOOLING_APPEND,'task_toml_append':NETWORK_APPEND},indent=2)+'\n')
            check_task(task,review_path)
            items.append({'task':name,'path':'tasks/'+name,'review':'reviews/'+name+'.json','runtime':'reviews/'+name+'-runtime.json','base':meta['ref']})
        record={'cohort':cohort,'stage':'prepared_not_executed','tasks':items,'selected_count':3,'original_candidate_cap_consumed':10,'target':3,
                'reward_semantics':'Continuous native patch similarity, never functional correctness/pass@1.','required_slots':2,'resource_reason':'Native task has no separate verifier image; Harbor resolves shared verifier; one controller plus one sandbox per serial trial.'}
        (destination/(cohort+'-cohort.json')).write_text(json.dumps(record,indent=2)+'\n');cohorts.append(record)
    report={'stage':'prepared_not_executed','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_sha256':'dcbf43f02a2a69014612a25341e1208c6fd881231f55d4c4404083b32e312841','selected':12,'cohorts':cohorts,'unselected':[x for x in sorted(checks) if x not in assets],'limitations':['No new generation candidates; original ten-per-repository allowances remain consumed.','Two nonapplying reference exports are excluded; other unselected exports remain outside this three-target runtime pilot.','No native similarity task is accepted until fresh no-model runtime controls pass.']}
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);args=parser.parse_args()
    result=prepare(args.destination);folder=ROOT/'evidence/prdiff-pilot-preparation';folder.mkdir(exist_ok=True)
    (folder/'selection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'selected':result['selected'],'cohorts':len(result['cohorts']),'new_generation_attempts':0}))
