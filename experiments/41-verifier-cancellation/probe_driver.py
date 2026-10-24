"""Native Harbor CLI, bounded cases, independent resource observations."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path('/work');OUT=ROOT/'evidence'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(value):(OUT/'probe-results.json').write_text(json.dumps(value,indent=2)+'\n')


def docker(*args,check=True):return subprocess.run(['/work/real/docker',*args],capture_output=True,text=True,check=check,timeout=30)


def inspect_resources(owner,expected_image):
    ids=docker('ps','-aq','--filter','label=biotasks.run='+owner).stdout.split();assert len(ids)==1
    row=json.loads(docker('inspect',ids[0]).stdout)[0];config=row['HostConfig']
    assert config['NanoCpus']==1000000000 and config['Memory']==6*1024**3 and config['MemorySwap']==6*1024**3
    assert config['NetworkMode']=='none' and row['Image']==expected_image
    assert row['Config']['Labels']['biotasks.run']==owner
    return dict(container_id=ids[0],image_id=row['Image'],nano_cpus=config['NanoCpus'],memory_bytes=config['Memory'],
        memory_swap_bytes=config['MemorySwap'],network=config['NetworkMode'],owner_label=owner,captured_ns=time.time_ns())


def main():
    owner=os.environ['BIOTASKS_RUN_ID'];family=json.loads((ROOT/'family.json').read_text());assert family['run_id']==owner
    assert not any(os.environ.get(k) for k in ['GH_TOKEN','GITHUB_TOKEN','OPENROUTER_API_KEY','CW_KEY_SECRET','HF_TOKEN'])
    assert importlib.metadata.version('harbor')=='0.6.6' and importlib.metadata.version('tenacity')=='9.2.1'
    source=Path(importlib.util.find_spec('harbor').origin).parent.parent
    parity=json.loads((ROOT/'package-source-pins.json').read_text())
    for row in parity:assert sha(source/row['path'])==row['sha256']
    (OUT/'native-source-parity.json').write_text(json.dumps(dict(source_files_verified=len(parity),harbor='0.6.6',tenacity='9.2.1',verified=True),indent=2)+'\n')
    jobs=Path(os.environ['BIOTASKS_SHARED_ROOT'])/'jobs';jobs.mkdir(exist_ok=True)
    result=dict(run_id=owner,package_source_verified=True,model_calls=0,cases=[]);save(result)
    for case in family['cases']:
        assert not docker('ps','-aq','--filter','label=biotasks.run='+owner).stdout.split(), 'No prior task may survive to a later case'
        task=ROOT/'outputs'/family['id']/case['task'];before={str(p.relative_to(task)):sha(p) for p in task.rglob('*') if p.is_file()}
        name=owner+'-'+case['name'];target=jobs/name;assert not target.exists()
        command=['/work/harbor066/bin/harbor','run','-p',str(task),'-a','nop','--env','docker','-n','1','-k','1','-r','0',
            '--override-cpus','1','--override-memory-mb','6144','-o',str(jobs),'--job-name',name]
        row=dict(name=case['name'],task=case['task'],command=command,started_ns=time.time_ns(),state='running');result['cases'].append(row);save(result)
        image=json.loads(docker('image','inspect',case['image_ref']).stdout)[0]
        assert image['Config']['Labels']['biotasks.run']==owner
        process=None
        try:
            with (OUT/(case['name']+'-harbor.log')).open('w') as log:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+90
                while process.poll() is None:
                    if 'resources' not in row and list(target.glob('*/verifier/process-events.jsonl')):
                        row['resources']=inspect_resources(owner,image['Id']);save(result)
                    if time.monotonic()>deadline:
                        row.update(state='outer_wrapper_timeout',uncertain_effect=True)
                        os.killpg(process.pid,signal.SIGTERM)
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                        break
                    time.sleep(0.1)
            row['wrapper_exit']=process.returncode
            if row['state']=='running':row['state']='native_returned'
            trials=list(target.glob('*/result.json'));assert len(trials)<=1
            row['trial_results']=[dict(path=str(p.relative_to(jobs)),sha256=sha(p),result=json.loads(p.read_text())) for p in trials]
            row['files']=[dict(path=str(p.relative_to(jobs)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(target.rglob('*')) if p.is_file()]
            after={str(p.relative_to(task)):sha(p) for p in task.rglob('*') if p.is_file()};assert before==after
            row['fixture_files_before']=before;row['fixture_files_after']=after
            row['finished_ns']=time.time_ns();save(result)
            if row.get('uncertain_effect') or row['wrapper_exit']!=0:break
            trial=row['trial_results'][0]['result'] if row['trial_results'] else {}
            if case['name']=='finite' and (trial.get('exception_info') or ((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward')!=0):
                result['remaining_cases_skipped']='Finite control did not establish a working native path';save(result);break
        finally:
            if process and process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
    result['finished_ns']=time.time_ns();save(result)


if __name__=='__main__':main()
