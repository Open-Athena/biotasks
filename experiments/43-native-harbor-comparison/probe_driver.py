"""Serial native comparison with the same outside observer for both packages."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from observer import snapshot

ROOT=Path('/work');OUT=ROOT/'evidence'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(value):(OUT/'probe-results.json').write_text(json.dumps(value,indent=2)+'\n')


def docker(*args,check=True):return subprocess.run(['/work/real/docker',*args],capture_output=True,text=True,timeout=30,check=check)


def stop_process(process):
    if process and process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)


def inspect_resources(owner,case,expected_image):
    ids=docker('ps','-aq','--filter','label=biotasks.run='+owner).stdout.split();assert len(ids)<=1
    if not ids:return None
    row=json.loads(docker('inspect',ids[0]).stdout)[0];host=row['HostConfig']
    assert row['Config']['Labels']['biotasks.case']==case['id'] and row['Config']['Labels']['biotasks.run']==owner
    assert host['NanoCpus']==1000000000 and host['Memory']==host['MemorySwap']==6*1024**3 and host['NetworkMode']=='none'
    assert row['Image']==expected_image
    return dict(container_id=ids[0],image_id=row['Image'],nano_cpus=host['NanoCpus'],memory_bytes=host['Memory'],
        memory_swap_bytes=host['MemorySwap'],network=host['NetworkMode'],owner_label=owner,case_label=case['id'],captured_ns=time.time_ns())


PARITY_SCRIPT="""
import hashlib,importlib.metadata,importlib.util,json,sys,time
from pathlib import Path
spec=json.loads(Path('/work/package-pins.json').read_text());version=sys.argv[1]
package=next(r for r in spec['packages'] if r['version']==version)
assert importlib.metadata.version('harbor')==version and importlib.metadata.version('tenacity')=='9.2.1'
assert time.timezone==0 and time.tzname==('UTC','UTC')
source=Path(importlib.util.find_spec('harbor').origin).parent.parent
for row in package['source_files']:
 with (source/row['path']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
print(json.dumps(dict(version=version,tenacity='9.2.1',source_files_verified=len(package['source_files']),timezone=list(time.tzname),verified=True)))
"""


def main():
    owner=os.environ['BIOTASKS_RUN_ID'];family=json.loads((ROOT/'family.json').read_text());assert family['run_id']==owner
    assert not any(os.environ.get(k) for k in ['GH_TOKEN','GITHUB_TOKEN','OPENROUTER_API_KEY','CW_KEY_ID','CW_KEY_SECRET','HF_TOKEN'])
    os.environ['TZ']='UTC'
    parity=[]
    for version,short in [('0.6.6','066'),('0.24.0','024')]:
        result=subprocess.run(['/work/harbor'+short+'/bin/python','-c',PARITY_SCRIPT,version],capture_output=True,text=True,timeout=30,check=True)
        parity.append(json.loads(result.stdout))
    (OUT/'native-source-parity.json').write_text(json.dumps(dict(packages=parity,verified=True),indent=2)+'\n')
    jobs=Path(os.environ['BIOTASKS_SHARED_ROOT'])/'jobs';jobs.mkdir(exist_ok=True)
    result=dict(run_id=owner,package_source_verified=True,timezone='UTC',observer_interval_seconds=0.5,model_calls=0,cases=[]);save(result)
    finite={}
    for case in family['cases']:
        assert not docker('ps','-aq','--filter','label=biotasks.run='+owner).stdout.split(), 'Prior task resource remains; stop comparison'
        if case['name']=='timeout' and not finite.get(case['version']):
            result['cases'].append(dict(id=case['id'],version=case['version'],name=case['name'],state='skipped_failed_finite_prerequisite'));save(result);continue
        task=ROOT/case['task_directory'];before={str(p.relative_to(task)):sha(p) for p in task.rglob('*') if p.is_file()}
        name=owner+'-'+case['id'];target=jobs/name;assert not target.exists()
        command=['/work/harbor'+case['short']+'/bin/harbor','run','-p',str(task),'-a','nop','--env','docker','-n','1','-k','1','-r','0',
            '--override-cpus','1','--override-memory-mb','6144','-o',str(jobs),'--job-name',name]
        row=dict(id=case['id'],version=case['version'],name=case['name'],task=case['task'],command=command,started_ns=time.time_ns(),state='running',observations=[])
        result['cases'].append(row);save(result)
        image=json.loads(docker('image','inspect',case['image_ref']).stdout)[0];assert image['Config']['Labels']['biotasks.run']==owner
        process=None;events=None;events_path=OUT/(case['id']+'-docker-events.jsonl')
        try:
            with (OUT/(case['id']+'-harbor.log')).open('w') as log,events_path.open('w') as event_log:
                events=subprocess.Popen(['/work/real/docker','events','--since',str(int(time.time())-1),'--filter','type=container',
                    '--filter','label=biotasks.run='+owner,'--filter','label=biotasks.case='+case['id'],'--format','{{json .}}'],stdout=event_log,stderr=subprocess.PIPE,start_new_session=True)
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+90
                while process.poll() is None:
                    assert events_path.stat().st_size<1024**2 and len(row['observations'])<180
                    if 'resources' not in row:
                        observed=inspect_resources(owner,case,image['Id'])
                        if observed:row['resources']=observed
                    if row.get('resources'):
                        try:observation=snapshot(row['resources']['container_id'])
                        except subprocess.TimeoutExpired:observation=dict(state='observer_exec_timeout',observer_finished_ns=time.time_ns())
                        row['observations'].append(observation);save(result)
                    if time.monotonic()>deadline:
                        row.update(state='outer_wrapper_timeout',uncertain_effect=True);stop_process(process);break
                    time.sleep(0.5)
                row['wrapper_exit']=process.returncode
            stop_process(events)
            row['docker_events_sha256']=sha(events_path);row['docker_events_bytes']=events_path.stat().st_size
            if row['state']=='running':row['state']='native_returned'
            trials=list(target.glob('*/result.json'));assert len(trials)<=1
            row['trial_results']=[dict(path=str(p.relative_to(jobs)),sha256=sha(p),result=json.loads(p.read_text())) for p in trials]
            row['files']=[dict(path=str(p.relative_to(jobs)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(target.rglob('*')) if p.is_file()]
            after={str(p.relative_to(task)):sha(p) for p in task.rglob('*') if p.is_file()};assert before==after
            row.update(fixture_files_before=before,fixture_files_after=after,finished_ns=time.time_ns());save(result)
            if row.get('uncertain_effect'):break
            trial=row['trial_results'][0]['result'] if row['trial_results'] else {}
            if case['name']=='finite':
                finite[case['version']]=bool(row['wrapper_exit']==0 and trial and not trial.get('exception_info') and ((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward')==0)
        finally:
            stop_process(process);stop_process(events)
    result['finished_ns']=time.time_ns();save(result)


if __name__=='__main__':main()
