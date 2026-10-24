"""Freeze one source-bound recorded-dependency case and portable initializer."""
import json
from pathlib import Path
import re
import shutil

from common import UPSTREAM,archive_tree,content_sha,json_sha,sha,write

ROOT=Path(__file__).resolve().parent
WORKER_FILES=['worker_job.py','supervisor_base.py','bootstrap_init.py','pinned_loader.py','recorded_replay.py',
    'docker_bridge.py','common.py','resume_runner.py','cleanup_owned.py','run_existing_controls.py','setup_controller.sh']
CLEANUP_FILES=['cleanup_job.py','cleanup_owned.py','common.py','resume_runner.py']
DATA_FILES=['bootstrap-dependency.json','recorded-actions.json','original-bootstrap.json','docker_original.py','runner_original.py','auth_original.py']


def main():
    prep=json.loads((ROOT/'candidate-preparation.json').read_text())
    descriptor=json.loads((ROOT/'bootstrap-dependency.json').read_text())
    prior=ROOT.parents[2]/'38/experiments/38-manifest-validation'
    original=json.loads((prior/'cohort.json').read_text())
    source=next(f for f in original['families'] if f['id']=='OHIF__Viewers')
    assert prep['upstream_revision']==UPSTREAM and prep['grading_assets_unchanged']==8
    frozen=ROOT/'inputs-private/portable';assert not frozen.exists();frozen.mkdir(mode=0o700)
    template=frozen/'tree';template.mkdir()
    for name in WORKER_FILES:shutil.copyfile(ROOT/name,template/name)
    for name in DATA_FILES:
        path=ROOT/name if name=='bootstrap-dependency.json' else ROOT/'inputs-private'/name
        if name.endswith('_original.py'):path=ROOT/'inputs-private/native-source'/name
        shutil.copyfile(path,template/name)
    bundle=ROOT/prep['task_bundle']['path'];assert sha(bundle)==prep['task_bundle']['sha256']
    shutil.copyfile(bundle,template/'tasks.tar.gz');shutil.copyfile(ROOT/'control-pins.json',template/'pins.json')
    baseline=ROOT.parents[3]/'experiments/28-catalogued-fields'
    notices=frozen/'notices';notices.mkdir()
    for spec in source['notices_bundle']['files']:
        name=spec['path']
        if name=='source-notices/Repo2RLEnv-LICENSE':path=baseline/'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
        elif '/history/' in name:path=baseline/'history-wide/source-notices'/name.removeprefix('source-notices/history/')
        else:path=baseline/'preflight/licenses'/name.removeprefix('source-notices/')
        assert sha(path)==spec['sha256']
        target=notices/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    notice_bundle=archive_tree(notices,frozen/'notices.tar.gz');notice_bundle['path']=str(Path(notice_bundle['path']).relative_to(ROOT))
    shutil.copyfile(frozen/'notices.tar.gz',template/'notices.tar.gz')
    task=dict(task=prep['task'],base_commit=prep['base_commit'],head_commit=prep['head_commit'],
        original_task_identity=prep['original_task_identity'],prepared_task_identity=prep['candidate_task_identity'],
        original_grading_assets_unchanged=8,files=prep['task_bundle']['files'],expected_f2p=26,expected_p2p=1189)
    test=(ROOT/'inputs-private/candidate/tree/outputs/OHIF__Viewers'/prep['task']/'tests/test.sh').read_text()
    exports=[line for line in test.splitlines() if line.startswith('export PATH=')]
    # Extract the actual subshell command and its first PATH export, not a guessed image default.
    commands=re.findall(r'^\( (export PATH=.*) \) > /logs/verifier/test_output.log 2>&1$',test,re.M)
    assert len(commands)==1 and len(exports)==1
    exports.append(commands[0].split(' && ',1)[0]);assert len(exports)==2
    resources=dict(original['families'][0]['resources'],maximum_cpu_hours=5,timeout_seconds=8400,work_deadline_seconds=7800)
    plan=dict(repositories=[dict(repo=prep['repo'],slug='OHIF__Viewers',tasks=[dict(task=task['task'],original_files=task['files'],proposed_arms_seconds=[300])])],model_calls=0,task_repairs=0)
    excluded=dict(original['exclusions']);rows=list(excluded['sources'])
    for path in [ROOT.parents[2]/'29/experiments/29-runtime-limits/ohif-recorded-submission.json',
                 ROOT.parents[2]/'29/experiments/29-runtime-limits/ohif-controls-submission.json',
                 prior/'runs/opencobra__cobrapy/submission.json',prior/'runs/scverse__scanpy/submission.json']:
        value=json.loads(path.read_text());assert value['worker_id'] and value['job_id']
        rows.append(dict(job_id=value['job_id'],worker_id=value['worker_id'],receipt_sha256=sha(path)))
    workers=sorted({r['worker_id'] for r in rows})
    excluded=dict(excluded_worker_ids=workers,excluded_worker_prefixes=sorted({w.rsplit('-worker-',1)[0] for w in workers}),sources=rows)
    family=dict(id='OHIF__Viewers',repo=prep['repo'],mode='recorded_bootstrap_dependency',tasks=[task],task_bundle=prep['task_bundle'],
        notices_bundle=notice_bundle,control_plan=plan,public_base_ref=descriptor['public_base_ref'],resources=resources,
        original_image_refs=sorted(set(source['original_image_refs']+['sha256:97437e1fef015e2767f7f27870ea72f0ec70b2e7db87996949b69ab8281ddc74'])),
        public_review_sha256=source['public_review_sha256'],effective_test_path_exports=exports,test_commands_sha256=content_sha(commands[0].encode()))
    # The public base is allowed to be cached; only earlier private task/bootstrap images must be absent.
    assert descriptor['expected_base_image_id'] not in family['original_image_refs']
    write(template/'family-template.json',family);write(template/'control-plan.json',plan)
    portable=archive_tree(template,frozen/'inputs.tar.gz');portable['path']=str(Path(portable['path']).relative_to(ROOT))
    cohort=dict(schema_version=1,issue=39,upstream_revision=UPSTREAM,source_plan_sha256=sha(ROOT/'source-plan.json'),
        source_ledger_sha256=original['source_ledger_sha256'],families=[family],exclusions=excluded,
        portable_input_bundle=portable,model_calls_enabled=False,new_capacity_allowed=False,original_cohort_tasks=83,new_unique_tasks=0)
    write(ROOT/'cohort.json',cohort)
    policy=dict(schema_version=1,issue=39,public_eligible=True,cohort_sha256=sha(ROOT/'cohort.json'),source_families={family['id']:json_sha(family)},
        source_reviews={family['id']:family['public_review_sha256']},scope='Original eligible OHIF source task and unchanged recorded commands, pinned Apache-2.0 upstream source/helpers, source notices, no-model isolated build/control logs and ownership provenance only; no images, node_modules, binaries, environments, credentials or biological datasets.',
        allowed_runtime_modes=['recorded_bootstrap_dependency'],excluded_repositories=['matchms/matchms'],
        retention='Retain while cited; no automatic deletion.',budget='Existing $10 archival reservation, no new paid tier or purchase.',
        initializer_required=True,task_dockerfile_alone_standalone=False)
    write(ROOT/'public-policy.json',policy)
    print(json.dumps(dict(portable_bytes=portable['bytes'],portable_files=len(portable['files']),tasks=1,model_calls=0,remote_admission=False)))


if __name__=='__main__':main()
