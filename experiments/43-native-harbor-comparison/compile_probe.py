"""Fixed serial comparison, immutable fixture bytes and owner-only metadata."""
import json
from pathlib import Path
import shutil
import zipfile
from common import archive_tree,inventory,json_sha,sha,write

ROOT=Path(__file__).resolve().parent
WORKER=['worker_job.py','supervisor_base.py','common.py','resume_runner.py','cleanup_owned.py','probe_driver.py','observer.py','setup_controller.sh']
CLEANUP=['cleanup_job.py','cleanup_owned.py','common.py','resume_runner.py']
BASE='python@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704'
BASE_ID='sha256:a33c10a97f11005523814c6eee013986119fe41f3122f444518117536675c8e1'


def main():
    packages=json.loads((ROOT/'package-acquisition.json').read_text());pins=json.loads((ROOT/'control-pins.json').read_text())
    prior=ROOT.parents[2]/'41/experiments/41-verifier-cancellation/fixture_writer.py'
    assert sha(ROOT/'fixture_writer.py')==sha(prior)
    resources=dict(cpus=2,memory_gib=12,disk_gib=12,controller_cpus=0.5,task_cpus=1,task_memory_gib=6,
        setup_timeout_seconds=900,timeout_seconds=3300,work_deadline_seconds=3000,maximum_cpu_hours=2,cleanup_allowance_cpu_hours=1/6)
    seed=dict(compiler_sha256=sha(Path(__file__)),worker_code={n:sha(ROOT/n) for n in WORKER},cleanup_code={n:sha(ROOT/n) for n in CLEANUP},
        writer_sha256=sha(ROOT/'fixture_writer.py'),packages_sha256=sha(ROOT/'package-acquisition.json'),pins=pins,resources=resources,
        baseline_constraints_sha256=sha(ROOT/'baseline-constraints.txt'),versions=['0.6.6','0.24.0'],cases=[['finite',2,5],['timeout',30,5]])
    run='biotasks43-compare-'+json_sha(seed)[:10];directory=ROOT/'inputs-private/probe';assert not directory.exists();directory.mkdir(mode=0o700)
    marker='biotasks41-comparison-'+run.rsplit('-',1)[1];tree=directory/'tree';cases=[]
    for version,short in [('0.6.6','066'),('0.24.0','024')]:
        for name,seconds in [('finite',2),('timeout',30)]:
            case_id=short+'-'+name;task='harbor-timeout-'+name;target=tree/'outputs'/('harbor_timeout_'+short)/task;target.mkdir(parents=True)
            (target/'environment').mkdir();(target/'tests').mkdir();image=run+'-'+case_id+':fixture'
            (target/'task.toml').write_text('version = "1.0"\n\n[metadata]\nname = "'+task+'"\ndescription = "Self-authored infrastructure fixture, not biological evaluation"\n\n[agent]\ntimeout_sec = 30\n\n[verifier]\ntimeout_sec = 5\n\n[verifier.env]\nFIXTURE_WRITER_SECONDS = "'+str(seconds)+'"\n\n[environment]\nbuild_timeout_sec = 120\ndocker_image = "'+image+'"\ncpus = 1\nmemory_mb = 6144\nstorage_mb = 1024\nallow_internet = false\n')
            (target/'instruction.md').write_text('Infrastructure-only nop fixture. Do not modify files or call a model. The verifier is a timed synthetic writer.\n')
            (target/'environment/docker-compose.yaml').write_text('services:\n  main:\n    image: '+image+'\n    pull_policy: never\n    cpus: 1.0\n    mem_limit: 6g\n    memswap_limit: 6g\n    network_mode: none\n    labels:\n      biotasks.run: "'+run+'"\n      biotasks.case: "'+case_id+'"\n    environment:\n      BIOTASKS_RUN_ID: "'+marker+'"\n      TZ: UTC\n')
            (target/'tests/test.sh').write_text('#!/usr/bin/env bash\nset -eu\npython3 /tests/writer.py > /logs/verifier/writer.log 2>&1\necho 0 > /logs/verifier/reward.txt\n');(target/'tests/test.sh').chmod(0o755)
            shutil.copyfile(ROOT/'fixture_writer.py',target/'tests/writer.py')
            cases.append(dict(id=case_id,version=version,short=short,name=name,task=task,task_directory=str(target.relative_to(tree)),writer_seconds=seconds,verifier_seconds=5,image_ref=image))
    bundle=archive_tree(tree,directory/'tasks.tar.gz');bundle['path']=str(Path(bundle['path']).relative_to(ROOT))
    notices=directory/'notices';notices.mkdir()
    for spec in packages['packages']+[dict(filename='tenacity-9.2.1-py3-none-any.whl',version='tenacity-9.2.1')]:
        with zipfile.ZipFile(ROOT/'inputs-private'/spec['filename']) as archive:
            names=[n for n in archive.namelist() if n.endswith('/licenses/LICENSE')];assert len(names)==1
            (notices/(spec['version']+'-LICENSE')).write_bytes(archive.read(names[0]))
    notice_bundle=archive_tree(notices,directory/'notices.tar.gz');notice_bundle['path']=str(Path(notice_bundle['path']).relative_to(ROOT))
    family=dict(id='harbor_comparison',repo='diagnostic/harbor-comparison',mode='harbor_timeout_diagnostic',cases=cases,
        task_bundle=bundle,notices_bundle=notice_bundle,resources=resources,public_base_ref=BASE,expected_public_base_id=BASE_ID,
        task_files=inventory(tree),writer_run_marker=marker,no_original_task_changes=True)
    cohort=dict(issue=43,families=[family],exclusions=dict(excluded_worker_ids=[],excluded_worker_prefixes=[]),model_calls_enabled=False,new_capacity_allowed=False)
    write(ROOT/'cohort.json',cohort);dest=ROOT/'inputs-private/payloads';dest.mkdir(mode=0o700);target=dest/family['id'];target.mkdir()
    for name in WORKER+['baseline-constraints.txt']:shutil.copyfile(ROOT/name,target/name)
    write(target/'pins.json',pins);write(target/'package-pins.json',packages)
    for name in ['harbor-0.6.6-py3-none-any.whl','harbor-0.24.0-py3-none-any.whl','tenacity-9.2.1-py3-none-any.whl']:shutil.copyfile(ROOT/'inputs-private'/name,target/name)
    shutil.copyfile(directory/'tasks.tar.gz',target/'tasks.tar.gz')
    config=dict(family,run_id=run,exclusions=cohort['exclusions'],source_family_sha256=json_sha(family),source_variant=family['mode']);write(target/'family.json',config)
    protected=dict(run_id=run,ref=BASE,image_id=BASE_ID);write(target/'protected-base.json',protected)
    manifest=dict(run_id=run,sha256={p.name:sha(p) for p in target.iterdir()},source_family_sha256=json_sha(family),model_calls=0);write(target/'payload.json',manifest)
    cleanup=dest/(family['id']+'-cleanup');cleanup.mkdir()
    for name in CLEANUP:shutil.copyfile(ROOT/name,cleanup/name)
    write(cleanup/'pins.json',pins);write(cleanup/'protected-base.json',protected);write(cleanup/'cleanup-payload.json',dict(primary_run_id=run,sha256={p.name:sha(p) for p in cleanup.iterdir()}))
    row=dict(id=family['id'],mode=family['mode'],run_id=run,resources=resources,payload_directory=str(target.relative_to(ROOT)),payload_manifest=manifest,
        payload_sha256={p.name:sha(p) for p in target.iterdir()},source_family_sha256=json_sha(family),cleanup_payload_directory=str(cleanup.relative_to(ROOT)),cleanup_payload_sha256={p.name:sha(p) for p in cleanup.iterdir()})
    write(ROOT/'runtime-plan.json',dict(issue=43,cohort_sha256=sha(ROOT/'cohort.json'),families=[row],model_calls_enabled=False,new_capacity_allowed=False,planned_cpu_hours=2+1/6))
    print(json.dumps(dict(run_id=run,cases=len(cases),fixture_files=len(bundle['files']),payload_files=len(row['payload_sha256']),admitted=False,model_calls=0)))


if __name__=='__main__':main()
