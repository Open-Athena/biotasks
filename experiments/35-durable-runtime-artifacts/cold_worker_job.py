"""Cold-worker native-inline controls; bounded infrastructure only, no task repairs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent
RUN='biotasks35-cobrapy-1482-inline-001'
assert os.environ['BIOTASKS_RUN_ID']==RUN
OUT=Path(os.environ['IRIS_OUTPUT_DIR'])
TOOLS=ROOT/'control-tools'
CONTROLLER=RUN+'-controller'
VOLUME=RUN+'-work'
REPORT={'run_id':RUN,'started':time.time(),'model_calls':0,'new_capacity':False}


def docker(*args,timeout=90,check=True):
    return subprocess.run([str(TOOLS/'docker'),*args],capture_output=True,text=True,timeout=timeout,check=check)


def fetch(url,path,sha,maximum):
    with urllib.request.urlopen(url,timeout=60) as src,path.open('wb') as dst:
        size=0
        while chunk:=src.read(1024*1024):
            size+=len(chunk);assert size<=maximum;dst.write(chunk)
    with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==sha


def interrupted(sig,frame):raise RuntimeError('signal '+str(sig))


def main():
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    OUT.mkdir(parents=True,exist_ok=True)
    pins=json.loads((ROOT/'pins.json').read_text())
    expected=json.loads((ROOT/'cold-worker-inputs.json').read_text())
    payload=json.loads((ROOT/'cold-payload.json').read_text())
    assert not any(os.environ.get(k) for k in ('OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN','CW_KEY_SECRET'))
    for name,value in payload['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value
    REPORT['payload_sha256']=payload['sha256']
    REPORT['worker_id']=os.environ['IRIS_WORKER_ID']
    assert REPORT['worker_id']==os.environ['BIOTASKS_EXPECTED_WORKER']
    assert REPORT['worker_id'] not in json.loads((ROOT/'original-workers.json').read_text())['excluded_worker_ids']
    REPORT['different_worker_verified']=True
    created=False
    deadline=time.time()+3000
    try:
        TOOLS.mkdir()
        fetch(pins['docker_url'],TOOLS/'docker.tgz',pins['docker_sha256'],100*1024**2)
        with tarfile.open(TOOLS/'docker.tgz') as t:(TOOLS/'docker').write_bytes(t.extractfile('docker/docker').read())
        (TOOLS/'docker').chmod(0o755)
        fetch(pins['compose_url'],TOOLS/'docker-compose',pins['compose_sha256'],100*1024**2)
        (TOOLS/'docker-compose').chmod(0o755)
        REPORT['original_image_absence']={}
        for ref in expected['original_worker_state_refs']:
            result=docker('image','inspect',ref,check=False)
            assert result.returncode!=0 and 'No such image' in result.stderr, 'Original image is present or inspection failed'
            REPORT['original_image_absence'][ref]=True
        REPORT['base_before']=json.loads(docker('image','inspect',expected['public_base_ref'],check=False).stdout or '[]')
        assert docker('volume','inspect',VOLUME,check=False).returncode!=0
        docker('volume','create','--label','biotasks.run='+RUN,VOLUME)
        mountpoint=json.loads(docker('volume','inspect',VOLUME).stdout)[0]['Mountpoint']
        docker('pull',pins['controller_image'],timeout=240)
        docker('create','--name',CONTROLLER,'--cpus=1','--memory=4g','--memory-swap=4g','--network=iris-egress','--label','biotasks.controller='+RUN,
               '-v','/var/run/docker.sock:/var/run/docker.sock','-v',VOLUME+':/work','-v',VOLUME+':'+mountpoint,'-w','/work',
               '-e','BIOTASKS_RUN_ID='+RUN,'-e','BIOTASKS_PHASE=controls','-e','BIOTASKS_SHARED_ROOT='+mountpoint,
               '-e','BIOTASKS_REAL_DOCKER=/work/real/docker','-e','DOCKER_CONFIG=/work/docker-config','-e','BIOTASKS29_BOUNDED_SUPERVISOR=1',
               pins['controller_image'],'sleep','3500')
        created=True;docker('start',CONTROLLER)
        docker('exec',CONTROLLER,'mkdir','-p','/work/real','/work/evidence','/work/harbor-bin','/work/docker-config/cli-plugins','/work/outputs','/work/infra')
        # Only fixed public inputs and selected original tasks; no credentials.
        for name in ['pins.json','setup_controller.sh','run_existing_controls.py','control-plan.json','original-tasks.tar.gz','cold-worker-inputs.json']:
            docker('cp',str(ROOT/name),CONTROLLER+':/work/'+name)
        for source,dest in [(TOOLS/'docker','/work/real/docker'),(TOOLS/'docker-compose','/work/docker-config/cli-plugins/docker-compose'),(ROOT/'harbor_docker_cold.py','/work/harbor-bin/docker')]:
            docker('cp',str(source),CONTROLLER+':'+dest)
        docker('exec',CONTROLLER,'chmod','+x','/work/harbor-bin/docker')
        docker('exec',CONTROLLER,'tar','-xzf','/work/original-tasks.tar.gz','-C','/work')
        with (OUT/'setup.log').open('w') as log:
            setup=subprocess.run([str(TOOLS/'docker'),'exec',CONTROLLER,'bash','/work/setup_controller.sh'],stdout=log,stderr=subprocess.STDOUT,timeout=900,check=False)
        REPORT['setup_exit']=setup.returncode
        assert setup.returncode==0,'Original controller setup failed'
        command=[str(TOOLS/'docker'),'exec','-e','PATH=/work/harbor-bin:/work/harbor066/bin:/usr/local/bin:/usr/bin:/bin',CONTROLLER,'timeout','--kill-after=15s',str(max(1,int(deadline-time.time()))),
                 'python','/work/run_existing_controls.py','--repo','opencobra/cobrapy','--tasks-root','/work','--jobs',mountpoint+'/jobs/cobrapy-1482-controls',
                 '--evidence','/work/evidence/controls','--deadline',str(deadline),'--execute']
        REPORT['controls_started']=time.time()
        with (OUT/'controller.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=max(1,deadline-time.time()+30),check=False)
        REPORT['controls_exit']=result.returncode;REPORT['controls_finished']=time.time()
    except Exception as error:
        REPORT['error_type']=type(error).__name__;REPORT['error']=str(error)[:500]
    finally:
        if (TOOLS/'docker').exists():
            # Stop owned task work before archiving, including after timeout.
            ids=docker('ps','-aq','--filter','label=biotasks.run='+RUN).stdout.split()
            if ids:docker('rm','-f',*ids)
            if created:
                try:
                    docker('exec',CONTROLLER,'tar','-czf','/work/evidence/control-artifacts.tar.gz','-C','/work','outputs','jobs','infra',timeout=120)
                    docker('cp',CONTROLLER+':/work/evidence/.',str(OUT),timeout=120)
                    REPORT['archive_copied']=True
                    REPORT['image_identities']=[json.loads(line) for line in (OUT/'image-identities.jsonl').read_text().splitlines()]
                    assert len(REPORT['image_identities'])==2
                    assert all(row['git_head']==expected['base_commit'] for row in REPORT['image_identities'])
                    REPORT['public_base_inspect']=json.loads(docker('image','inspect',expected['public_base_ref']).stdout)[0]
                except Exception as error:REPORT['archive_error']=type(error).__name__
            from cleanup_owned import cleanup
            REPORT['cleanup']=cleanup(TOOLS/'docker',RUN)
        if TOOLS.exists():shutil.rmtree(TOOLS)
        REPORT['finished']=time.time()
        for path in OUT.rglob('*'):
            if path.is_file() and path.name!='control-result.json':
                with path.open('rb') as stream:REPORT.setdefault('output_sha256',{})[str(path.relative_to(OUT))]=hashlib.file_digest(stream,'sha256').hexdigest()
        (OUT/'control-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
        print('BIOTASKS35_COLD='+json.dumps(REPORT),flush=True)
    assert REPORT.get('controls_exit')==0 and REPORT.get('cleanup',{}).get('verified_empty') and REPORT.get('archive_copied') and len(REPORT.get('image_identities',[]))==2

if __name__=='__main__':main()
