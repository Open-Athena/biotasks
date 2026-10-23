"""Bounded recipe reconstruction and frozen target-selection comparison; no repairs."""
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
OWNER='biotasks32-matchms-targets-001'
assert os.environ['BIOTASKS_RUN_ID']==OWNER
LABEL='org.open-athena.biotasks.owner='+OWNER
TOOLS=ROOT/'build-tools'
CONTEXT=ROOT/'build-context'
OUT=Path(os.environ['IRIS_OUTPUT_DIR'])
REPORT={'run_id':OWNER,'model_calls':0,'new_capacity':False,'controls_run':0,'started':time.time()}


def docker(*args,timeout=30,check=True):
    return subprocess.run([str(TOOLS/'docker'),*args],capture_output=True,text=True,timeout=timeout,check=check)


def stop(sig, frame):raise RuntimeError('signal '+str(sig))


def main():
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGALRM,stop);signal.alarm(8400)
    OUT.mkdir(parents=True,exist_ok=True)
    pins=json.loads((ROOT/'docker-tool.json').read_text())
    boot=json.loads((ROOT/'bootstrap.json').read_text())
    assert boot['repo']=='matchms/matchms' and boot['ref']=='50baefdb0ce9401aac55cc2a09d07421dd684481'
    REPORT['bootstrap_record_sha256']=hashlib.sha256((ROOT/'bootstrap.json').read_bytes()).hexdigest()
    tag=OWNER+':original-recipe'
    try:
        TOOLS.mkdir()
        archive=TOOLS/'docker.tgz'
        with urllib.request.urlopen(pins['docker_url'],timeout=60) as src,archive.open('wb') as dst:
            size=0
            while chunk:=src.read(1024*1024):
                size+=len(chunk);assert size<100*1024**2;dst.write(chunk)
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==pins['docker_sha256']
        with tarfile.open(archive) as tf:(TOOLS/'docker').write_bytes(tf.extractfile('docker/docker').read())
        (TOOLS/'docker').chmod(0o755);archive.unlink()
        assert not docker('ps','-aq','--filter','label='+LABEL).stdout.strip()
        assert docker('image','inspect',tag,check=False).returncode!=0
        info=json.loads(docker('info','--format','{{json .}}').stdout)
        assert info['MemoryLimit'] and info['CpuCfsQuota']
        CONTEXT.mkdir()
        def git(*args):
            return subprocess.run(['git',*args],cwd=CONTEXT,capture_output=True,text=True,timeout=180,check=True).stdout.strip()
        git('init','-q');git('remote','add','origin','https://github.com/matchms/matchms.git')
        git('fetch','--depth=1','origin',boot['ref']);git('checkout','--detach','FETCH_HEAD')
        assert git('rev-parse','HEAD')==boot['ref']
        REPORT['source_commit']=boot['ref']
        recipe=boot['dockerfile_reconstruction']
        assert recipe.count('FROM ')==1
        # An ownership label is the sole recipe adaptation; all RUN/COPY/base
        # instructions are byte-preserved. It labels build intermediates too.
        lines=recipe.splitlines(keepends=True)
        index=next(i for i,line in enumerate(lines) if line.startswith('FROM '))+1
        lines.insert(index,'LABEL '+LABEL+'\n')
        adjusted=''.join(lines)
        assert adjusted.replace('LABEL '+LABEL+'\n','',1)==recipe
        dockerfile=ROOT/'Dockerfile.owned';dockerfile.write_text(adjusted)
        REPORT['recipe_sha256']=hashlib.sha256(recipe.encode()).hexdigest()
        REPORT['adapted_recipe_sha256']=hashlib.sha256(adjusted.encode()).hexdigest()
        REPORT['recipe_adaptation']='Ownership LABEL after FROM only; no command or dependency repairs'
        env={**os.environ,'DOCKER_BUILDKIT':'0'}
        command=[str(TOOLS/'docker'),'build','--force-rm','--cpu-period=100000','--cpu-quota=150000','--memory=6g','--memory-swap=6g','--network=iris-egress','--label',LABEL,'--tag',tag,'-f',str(dockerfile),str(CONTEXT)]
        REPORT['build_started']=time.time()
        with (OUT/'build.log').open('w') as log:
            result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800,check=False)
        REPORT['build_exit']=result.returncode
        REPORT['build_finished']=time.time()
        if result.returncode==0:
            img=json.loads(docker('image','inspect',tag).stdout)[0]
            assert img['Config']['Labels']['org.open-athena.biotasks.owner']==OWNER
            REPORT['image_id']=img['Id']
            env={**os.environ,'PATH':str(TOOLS)+os.pathsep+os.environ['PATH'],
                 'BIOTASKS32_BOUNDED_SUPERVISOR':'1','PYTHONDONTWRITEBYTECODE':'1'}
            with (OUT/'driver.log').open('w') as log:
                comparison=subprocess.run([os.environ['IRIS_PYTHON'],'-B',str(ROOT/'live_validation.py'),
                    '--image',img['Id'],'--owner',OWNER,'--output',str(OUT/'comparison')],
                    env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
            REPORT['comparison_exit']=comparison.returncode
    except Exception as error:
        REPORT['error_type']=type(error).__name__
        REPORT['error']=str(error)[:500]
    finally:
        signal.alarm(300)
        if (TOOLS/'docker').exists():
            ids=docker('ps','-aq','--filter','label='+LABEL).stdout.split()
            if ids:docker('rm','-f',*ids,timeout=120)
            REPORT['owned_containers_absent']=not docker('ps','-aq','--filter','label='+LABEL).stdout.strip()
            for attempt in range(16):
                image_ids=set(docker('image','ls','-aq','--no-trunc','--filter','label='+LABEL).stdout.split())
                if not image_ids:break
                removed=False
                for image_id in image_ids:
                    checked=docker('image','inspect',image_id,check=False)
                    if checked.returncode:continue
                    details=json.loads(checked.stdout)[0]
                    assert details['Config']['Labels']['org.open-athena.biotasks.owner']==OWNER
                    result=docker('image','rm','-f',image_id,timeout=30,check=False)
                    removed|=result.returncode==0
                if not removed:break
            REPORT['owned_image_ids_remaining']=docker('image','ls','-aq','--filter','label='+LABEL).stdout.split()
        for path in [CONTEXT,TOOLS]:
            if path.exists():shutil.rmtree(path)
        if (ROOT/'Dockerfile.owned').exists():(ROOT/'Dockerfile.owned').unlink()
        REPORT['local_context_tools_removed']=not CONTEXT.exists() and not TOOLS.exists()
        if (OUT/'build.log').exists():
            with (OUT/'build.log').open('rb') as stream:REPORT['build_log_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        REPORT['finished']=time.time()
        (OUT/'live-supervisor-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
        signal.alarm(0)
        print('BIOTASKS32_LIVE='+json.dumps(REPORT),flush=True)
    assert REPORT.get('build_exit')==0 and REPORT.get('comparison_exit')==0 and REPORT.get('owned_containers_absent') and not REPORT.get('owned_image_ids_remaining'), 'Incomplete comparison or cleanup: inspect evidence, do not repair or resubmit'

if __name__=='__main__':main()
