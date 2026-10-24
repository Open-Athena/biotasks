"""Compile fixed handles exclusively from verified anonymous input readback."""
import json
from pathlib import Path
import shutil

from common import inventory,json_sha,sha,write
from freeze_runtime import WORKER_FILES,DATA_FILES,CLEANUP_FILES

ROOT=Path(__file__).resolve().parent


def main():
    cohort=json.loads((ROOT/'cohort.json').read_text());cold=json.loads((ROOT/'cold-input-readback.json').read_text())
    source=ROOT/cold['runtime_input_root'];assert cold['anonymous_download_verified']
    assert inventory(source)==cohort['portable_input_bundle']['files']
    assert cold['archive_sha256']==cohort['portable_input_bundle']['sha256']
    family=cohort['families'][0];assert family['mode']=='recorded_bootstrap_dependency'
    assert json.loads((source/'family-template.json').read_text())==family
    assert all(sha(ROOT/name)==sha(source/name) for name in WORKER_FILES)
    identity=dict(portable_sha256=cold['archive_sha256'],family_sha256=json_sha(family),
        cleanup_code={n:sha(ROOT/n) for n in CLEANUP_FILES},exclusions=cohort['exclusions'])
    run='biotasks39-ohif-viewers-'+json_sha(identity)[:10]
    dest=ROOT/'inputs-private/payloads';assert not dest.exists();dest.mkdir(mode=0o700)
    target=dest/family['id'];target.mkdir()
    for name in WORKER_FILES+DATA_FILES+['tasks.tar.gz','pins.json','control-plan.json']:shutil.copyfile(source/name,target/name)
    config={k:family[k] for k in ['id','repo','mode','tasks','task_bundle','resources','original_image_refs','public_base_ref','effective_test_path_exports','test_commands_sha256']}
    config.update(run_id=run,exclusions=cohort['exclusions'],source_family_sha256=json_sha(family),source_variant=family['mode'],upstream_revision=cohort['upstream_revision'])
    write(target/'family.json',config)
    manifest=dict(run_id=run,sha256={p.name:sha(p) for p in target.iterdir()},source_family_sha256=json_sha(family),
        portable_input_sha256=cold['archive_sha256'],input_manifest_sha256=sha(ROOT/'input-evidence-manifest.json'),model_calls=0,task_repairs=0)
    write(target/'payload.json',manifest)
    cleanup=dest/(family['id']+'-cleanup');cleanup.mkdir()
    for name in CLEANUP_FILES:shutil.copyfile(ROOT/name,cleanup/name)
    shutil.copyfile(ROOT/'control-pins.json',cleanup/'pins.json')
    write(cleanup/'cleanup-payload.json',dict(primary_run_id=run,sha256={p.name:sha(p) for p in cleanup.iterdir()}))
    row=dict(id=family['id'],mode=family['mode'],run_id=run,resources=family['resources'],
        payload_directory=str(target.relative_to(ROOT)),payload_manifest=manifest,payload_sha256={p.name:sha(p) for p in target.iterdir()},
        source_family_sha256=json_sha(family),cleanup_payload_directory=str(cleanup.relative_to(ROOT)),cleanup_payload_sha256={p.name:sha(p) for p in cleanup.iterdir()})
    write(ROOT/'runtime-plan.json',dict(schema_version=1,issue=39,cohort_sha256=sha(ROOT/'cohort.json'),families=[row],
        model_calls_enabled=False,new_capacity_allowed=False,planned_cpu_hours=5+1/6,cold_inputs_verified=True))
    print(json.dumps(dict(fixed_handle=run,tasks=1,planned_not_admitted_cpu_hours=5+1/6,model_calls=0)))


if __name__=='__main__':main()
