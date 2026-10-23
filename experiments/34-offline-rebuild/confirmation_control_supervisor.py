"""Controls-only supervisor reusing original Harbor setup/resource wrapper."""
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
RUN='biotasks34-macs-742-confirm-001'
BUILD_OWNER=RUN+'-image'
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
    expected=json.loads((ROOT/'reconstruction-result.json').read_text())
    created=False
    deadline=time.time()+3000
    try:
        TOOLS.mkdir()
        fetch(pins['docker_url'],TOOLS/'docker.tgz',pins['docker_sha256'],100*1024**2)
        with tarfile.open(TOOLS/'docker.tgz') as t:(TOOLS/'docker').write_bytes(t.extractfile('docker/docker').read())
        (TOOLS/'docker').chmod(0o755)
        fetch(pins['compose_url'],TOOLS/'docker-compose',pins['compose_sha256'],100*1024**2)
        (TOOLS/'docker-compose').chmod(0o755)
        image=json.loads(docker('image','inspect',expected['retained_image']).stdout)[0]
        assert image['Id']==expected['image_id'] and image['Config']['Labels']['org.open-athena.biotasks.owner']==BUILD_OWNER
        REPORT['bootstrap_image_id']=image['Id']
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
        for name in ['pins.json','setup_controller.sh','run_existing_controls.py','control-plan.json','original-tasks.tar.gz']:
            docker('cp',str(ROOT/name),CONTROLLER+':/work/'+name)
        for source,dest in [(TOOLS/'docker','/work/real/docker'),(TOOLS/'docker-compose','/work/docker-config/cli-plugins/docker-compose'),(ROOT/'harbor_docker_receipts.py','/work/harbor-bin/docker'),(ROOT/'capture_build_receipt.py','/work/harbor-bin/capture_build_receipt.py')]:
            docker('cp',str(source),CONTROLLER+':'+dest)
        docker('exec',CONTROLLER,'chmod','+x','/work/harbor-bin/docker')
        docker('exec',CONTROLLER,'tar','-xzf','/work/original-tasks.tar.gz','-C','/work')
        with (OUT/'setup.log').open('w') as log:
            setup=subprocess.run([str(TOOLS/'docker'),'exec',CONTROLLER,'bash','/work/setup_controller.sh'],stdout=log,stderr=subprocess.STDOUT,timeout=900,check=False)
        REPORT['setup_exit']=setup.returncode
        assert setup.returncode==0,'Original controller setup failed'
        command=[str(TOOLS/'docker'),'exec','-e','PATH=/work/harbor-bin:/work/harbor066/bin:/usr/local/bin:/usr/bin:/bin',CONTROLLER,'timeout','--kill-after=15s',str(max(1,int(deadline-time.time()))),
                 'python','/work/run_existing_controls.py','--repo','macs3-project/MACS','--tasks-root','/work','--jobs',mountpoint+'/jobs/macs-742-controls',
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
                    REPORT['dependency_receipts']=[]
                    records=(OUT/'build-receipts.jsonl').read_text().splitlines()
                    assert len(records)==2, 'Expected a receipt bound to each control build'
                    for line in records:
                        item=json.loads(line)
                        rel=Path(item['file'])
                        assert not rel.is_absolute() and '..' not in rel.parts
                        raw=(OUT/rel).read_bytes()
                        assert hashlib.sha256(raw).hexdigest()==item['sha256']
                        from capture_build_receipt import validate_receipt
                        validate_receipt(json.loads(raw))
                        REPORT['dependency_receipts'].append(item)
                except Exception as error:REPORT['archive_error']=type(error).__name__
            from cleanup_owned import cleanup
            REPORT['cleanup']=cleanup(TOOLS/'docker',RUN)
            # Keep reconstruction image until archive readback, even if controls
            # fail. A later explicit owned cleanup records final image absence.
            REPORT['retained_reconstruction_image']=expected.get('retained_image')
        if TOOLS.exists():shutil.rmtree(TOOLS)
        REPORT['finished']=time.time()
        for path in OUT.rglob('*'):
            if path.is_file() and path.name!='control-result.json':
                with path.open('rb') as stream:REPORT.setdefault('output_sha256',{})[str(path.relative_to(OUT))]=hashlib.file_digest(stream,'sha256').hexdigest()
        (OUT/'control-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
        print('BIOTASKS34_CONTROLS='+json.dumps(REPORT),flush=True)
    assert REPORT.get('controls_exit')==0 and REPORT.get('cleanup',{}).get('verified_empty') and REPORT.get('archive_copied') and len(REPORT.get('dependency_receipts',[]))==2

if __name__=='__main__':main()
