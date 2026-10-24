"""Compile data-only family payloads with identical worker code and fixed handles."""
import json
from pathlib import Path
import shutil

from common import content_sha,json_sha,run_name,sha,unpack_task_archive,write
from evidence import archive_records,verify_imported_failure
from prepare_inputs import staged_object

ROOT=Path(__file__).resolve().parent
WORKER_FILES=['batch_job.py','docker_bridge.py','common.py','cleanup_owned.py',
    'run_existing_controls.py','setup_controller.sh']
CLEANUP_FILES=['cleanup_job.py','cleanup_owned.py','common.py']


def main():
    cohort=json.loads((ROOT/'cohort.json').read_text())
    source_plan=json.loads((ROOT/'source-plan.json').read_text())
    assert sha(ROOT/'source-plan.json')==cohort['source_plan_sha256']
    assert sha(source_plan['source_ledger'])==cohort['source_ledger_sha256']
    destination=ROOT/'inputs-private/payloads';assert not destination.exists();destination.mkdir(mode=0o700)
    code={name:sha(ROOT/name) for name in WORKER_FILES}
    plans=[]
    for family in cohort['families']:
        if family['mode']=='reference_stop':
            for name in ['evidence/runtime.tar.zst','evidence/native-task.tar.gz','provenance/runtime-readback.json']:
                source,row=staged_object(source_plan['failure_manifest'],source_plan['failure_receipt'],source_plan['failure_staging'],name)
                assert sha(ROOT/'inputs-private/acquired/failure-reference'/Path(name).name)==row['sha256']
            failure=verify_imported_failure(ROOT/'inputs-private/acquired/failure-reference',
                ROOT/'inputs-private/acquired'/family['id']/'prepared')
            assert failure==family['imported_failure']
            source,row=staged_object(source_plan['candidate_manifest'],source_plan['candidate_receipt'],source_plan['candidate_staging'],'evidence/candidate-tasks.tar.gz')
            canonical=archive_records(source,'tar.gz')
            frozen=archive_records(ROOT/family['task_bundle']['path'],'tar.gz')
            assert {name:(r['sha256'],r['mode']) for name,r in canonical.items()}=={name:(r['sha256'],r['mode']) for name,r in frozen.items()}
            plans.append(dict(id=family['id'],mode=family['mode'],run_id=None,
                source_family_sha256=json_sha(family),imported_failure=family['imported_failure'],
                source_failure_manifest_sha256=sha(source_plan['failure_manifest']),
                source_candidate_manifest_sha256=sha(source_plan['candidate_manifest'])))
            continue
        assert family['mode']=='native_inline'
        bundle=ROOT/family['task_bundle']['path']
        assert sha(bundle)==family['task_bundle']['sha256']
        unpack_task_archive(bundle,family['task_bundle']['files'],None)
        prefix=ROOT/family['bootstrap_prefix_file'];assert sha(prefix)==family['bootstrap_prefix_sha256']
        # Code/resources/lineage affect the handle; the handle itself is excluded.
        identity=dict(family_sha256=json_sha(family),worker_code_sha256=code,
            cleanup_code_sha256={name:sha(ROOT/name) for name in CLEANUP_FILES},
            pins_sha256=sha(ROOT/'control-pins.json'),exclusions=cohort['exclusions'])
        run=run_name(family['repo'],json_sha(identity))
        config={key:family[key] for key in ['id','repo','mode','tasks','task_bundle',
            'resources','original_image_refs','public_base_ref','bootstrap_prefix_sha256']}
        config.update(run_id=run,exclusions=cohort['exclusions'],source_family_sha256=json_sha(family),
            source_variant=family['mode'],upstream_revision=cohort['upstream_revision'])
        target=destination/family['id'];target.mkdir()
        for name in WORKER_FILES:shutil.copyfile(ROOT/name,target/name)
        for path,name in [(ROOT/'control-pins.json','pins.json'),(bundle,'tasks.tar.gz'),(prefix,'bootstrap-prefix.Dockerfile')]:
            shutil.copyfile(path,target/name)
        write(target/'family.json',config);write(target/'control-plan.json',family['control_plan'])
        hashes={p.name:sha(p) for p in target.iterdir() if p.is_file()}
        manifest=dict(run_id=run,sha256=hashes,worker_code_sha256=code,
            source_family_sha256=json_sha(family),model_calls=0,task_repairs=0)
        write(target/'payload.json',manifest)
        cleanup=destination/(family['id']+'-cleanup');cleanup.mkdir()
        for name in CLEANUP_FILES:shutil.copyfile(ROOT/name,cleanup/name)
        shutil.copyfile(ROOT/'control-pins.json',cleanup/'pins.json')
        cleanup_manifest=dict(primary_run_id=run,sha256={p.name:sha(p) for p in cleanup.iterdir()})
        write(cleanup/'cleanup-payload.json',cleanup_manifest)
        plans.append(dict(id=family['id'],mode=family['mode'],run_id=run,resources=family['resources'],
            payload_directory=str(target.relative_to(ROOT)),payload_manifest=manifest,
            payload_sha256={p.name:sha(p) for p in target.iterdir() if p.is_file()},source_family_sha256=json_sha(family),
            cleanup_payload_directory=str(cleanup.relative_to(ROOT)),
            cleanup_payload_sha256={p.name:sha(p) for p in cleanup.iterdir()}))
    result=dict(schema_version=1,issue=38,cohort_sha256=sha(ROOT/'cohort.json'),families=plans,
        worker_code_sha256=code,model_calls_enabled=False,new_capacity_allowed=False,
        planned_cpu_hours=sum(f['resources']['maximum_cpu_hours']+f['resources']['cleanup_allowance_cpu_hours']
            for f in plans if f['mode']=='native_inline'))
    write(ROOT/'runtime-plan.json',result)
    print(json.dumps(dict(compiled_family_payloads=sum(f['mode']=='native_inline' for f in plans),
        identical_worker_code=True,planned_not_booked_cpu_hours=result['planned_cpu_hours'],model_calls=0)))


if __name__=='__main__':main()
