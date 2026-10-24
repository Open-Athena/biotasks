"""Data-only synthetic fixture and fixed handle; no model/remote calls."""
import json
from pathlib import Path
import shutil

from common import archive_tree,inventory,json_sha,sha,write

ROOT=Path(__file__).resolve().parent
WORKER=['worker_job.py','supervisor_base.py','common.py','resume_runner.py','cleanup_owned.py','probe_driver.py','setup_controller.sh']
CLEANUP=['cleanup_job.py','cleanup_owned.py','common.py','resume_runner.py']
BASE='python@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704'
BASE_ID='sha256:a33c10a97f11005523814c6eee013986119fe41f3122f444518117536675c8e1'


def main():
    assert json.loads((ROOT/'cancellation-checks.json').read_text())['successful']
    source=json.loads((ROOT/'package-acquisition.json').read_text());dep=json.loads((ROOT/'test-dependency-acquisition.json').read_text())
    pins=json.loads((ROOT/'control-pins.json').read_text());pins.update(tenacity_version='9.2.1',tenacity_wheel_sha256=dep['wheel_sha256'])
    write(ROOT/'control-pins.json',pins)
    allowance=json.loads((ROOT/'retry-allowance.json').read_text())
    maximum=allowance['remaining_main_cpu_hours']
    assert 0<maximum<1 and maximum+allowance['prior_actual_cpu_hours']==1
    timeout=int(maximum*3600/2)-300
    r=dict(cpus=2,memory_gib=12,disk_gib=8,controller_cpus=0.5,task_cpus=1,task_memory_gib=6,
        setup_timeout_seconds=600,timeout_seconds=timeout,work_deadline_seconds=timeout-300,maximum_cpu_hours=maximum,cleanup_allowance_cpu_hours=1/6)
    seed=dict(worker_code={n:sha(ROOT/n) for n in WORKER},cleanup_code={n:sha(ROOT/n) for n in CLEANUP},
        writer_sha256=sha(ROOT/'fixture_writer.py'),source_pins_sha256=sha(ROOT/'package-acquisition.json'),
        dependency_pins_sha256=sha(ROOT/'test-dependency-acquisition.json'),pins=pins,resources=r,
        cases=[dict(name='finite',seconds=2,verifier=5),dict(name='timeout',seconds=30,verifier=5)])
    run='biotasks41-cancel-'+json_sha(seed)[:10];directory=ROOT/'inputs-private/probe';assert not directory.exists();directory.mkdir(mode=0o700)
    tree=directory/'tree';cases=[]
    for name,seconds in [('finite',2),('timeout',30)]:
        task='harbor-timeout-'+name;target=tree/'outputs/harbor_timeout'/task;target.mkdir(parents=True)
        (target/'environment').mkdir();(target/'tests').mkdir()
        image=run+'-'+name+':fixture'
        (target/'task.toml').write_text('version = "1.0"\n\n[metadata]\nname = "'+task+'"\ndescription = "Self-authored infrastructure fixture, not biological evaluation"\n\n[agent]\ntimeout_sec = 30\n\n[verifier]\ntimeout_sec = 5\n\n[verifier.env]\nFIXTURE_WRITER_SECONDS = "'+str(seconds)+'"\n\n[environment]\nbuild_timeout_sec = 120\ndocker_image = "'+image+'"\ncpus = 1\nmemory_mb = 6144\nstorage_mb = 1024\nallow_internet = false\n')
        (target/'instruction.md').write_text('Infrastructure-only nop fixture. Do not modify files or call a model. The verifier is a timed synthetic writer.\n')
        (target/'environment/docker-compose.yaml').write_text('services:\n  main:\n    image: '+image+'\n    build: null\n    pull_policy: never\n    cpus: 1.0\n    mem_limit: 6g\n    memswap_limit: 6g\n    network_mode: none\n    labels:\n      biotasks.run: "'+run+'"\n    environment:\n      BIOTASKS_RUN_ID: "'+run+'"\n')
        (target/'tests/test.sh').write_text('#!/usr/bin/env bash\nset -eu\npython3 /tests/writer.py > /logs/verifier/writer.log 2>&1\necho 0 > /logs/verifier/reward.txt\n')
        (target/'tests/test.sh').chmod(0o755);shutil.copyfile(ROOT/'fixture_writer.py',target/'tests/writer.py')
        cases.append(dict(name=name,task=task,writer_seconds=seconds,verifier_seconds=5,image_ref=image))
    bundle=archive_tree(tree,directory/'tasks.tar.gz');bundle['path']=str(Path(bundle['path']).relative_to(ROOT))
    notices=directory/'notices';notices.mkdir()
    for acq,base,label in [(source,ROOT/'inputs-private/source','harbor'),(dep,ROOT/'inputs-private/check-dependency/source','tenacity')]:
        for row in acq['source_files']:
            if '/licenses/' in row['path']:
                path=base/row['path'];assert sha(path)==row['sha256'];shutil.copyfile(path,notices/(label+'-LICENSE'))
    notice_bundle=archive_tree(notices,directory/'notices.tar.gz');notice_bundle['path']=str(Path(notice_bundle['path']).relative_to(ROOT))
    family=dict(id='harbor_timeout',repo='diagnostic/harbor-timeout',mode='harbor_timeout_diagnostic',cases=cases,
        task_bundle=bundle,notices_bundle=notice_bundle,resources=r,public_base_ref=BASE,expected_public_base_id=BASE_ID,
        task_files=inventory(tree),no_original_task_changes=True)
    cohort=dict(issue=41,families=[family],exclusions=dict(excluded_worker_ids=[],excluded_worker_prefixes=[]),
        source_assessment_sha256=sha(ROOT/'source-assessment.json'),model_calls_enabled=False,new_capacity_allowed=False)
    write(ROOT/'cohort.json',cohort)
    dest=ROOT/'inputs-private/payloads';dest.mkdir(mode=0o700);target=dest/family['id'];target.mkdir()
    for name in WORKER:shutil.copyfile(ROOT/name,target/name)
    write(target/'pins.json',pins);write(target/'package-source-pins.json',source['source_files']);shutil.copyfile(directory/'tasks.tar.gz',target/'tasks.tar.gz')
    for path in [ROOT/'inputs-private/harbor-0.6.6-py3-none-any.whl',ROOT/'inputs-private/check-dependency/tenacity-9.2.1-py3-none-any.whl']:shutil.copyfile(path,target/path.name)
    config=dict(family,run_id=run,exclusions=cohort['exclusions'],source_family_sha256=json_sha(family),source_variant=family['mode'])
    write(target/'family.json',config)
    protected=dict(run_id=run,ref=BASE,image_id=BASE_ID);write(target/'protected-base.json',protected)
    manifest=dict(run_id=run,sha256={p.name:sha(p) for p in target.iterdir()},source_family_sha256=json_sha(family),model_calls=0)
    write(target/'payload.json',manifest)
    cleanup=dest/(family['id']+'-cleanup');cleanup.mkdir()
    for name in CLEANUP:shutil.copyfile(ROOT/name,cleanup/name)
    write(cleanup/'pins.json',pins);write(cleanup/'protected-base.json',protected);write(cleanup/'cleanup-payload.json',dict(primary_run_id=run,sha256={p.name:sha(p) for p in cleanup.iterdir()}))
    row=dict(id=family['id'],mode=family['mode'],run_id=run,resources=r,payload_directory=str(target.relative_to(ROOT)),payload_manifest=manifest,
        payload_sha256={p.name:sha(p) for p in target.iterdir()},source_family_sha256=json_sha(family),
        cleanup_payload_directory=str(cleanup.relative_to(ROOT)),cleanup_payload_sha256={p.name:sha(p) for p in cleanup.iterdir()})
    write(ROOT/'runtime-plan.json',dict(issue=41,cohort_sha256=sha(ROOT/'cohort.json'),families=[row],model_calls_enabled=False,new_capacity_allowed=False,planned_cpu_hours=maximum+1/6))
    print(json.dumps(dict(run_id=run,cases=2,fixture_files=len(bundle['files']),payload_files=len(row['payload_sha256']),model_calls=0,admitted=False)))


if __name__=='__main__':main()
