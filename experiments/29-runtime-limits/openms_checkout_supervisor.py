"""Two bounded acquisition-only arms in fresh original-controller images."""
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
RUN='biotasks29-openms-checkout-001'
LABEL='org.open-athena.biotasks.owner='+RUN
OUT=Path(os.environ['IRIS_OUTPUT_DIR'])
TOOLS=ROOT/'checkout-tools'
WORK_DEADLINE=None
CLEANUP=False
REPORT={'run_id':RUN,'model_calls':0,'new_capacity':False,'arms':[],'started':time.time()}


def docker(*args,timeout=30,check=True):
    if not CLEANUP and WORK_DEADLINE is not None and time.monotonic()+timeout>WORK_DEADLINE:
        raise RuntimeError('Full operation allowance does not fit work deadline')
    return subprocess.run([str(TOOLS/'docker'),*args],capture_output=True,text=True,timeout=timeout,check=check)


def main():
    global WORK_DEADLINE,CLEANUP
    assert os.environ['BIOTASKS_RUN_ID']==RUN
    assert not any(os.environ.get(k) for k in ('GH_TOKEN','GITHUB_TOKEN','OPENROUTER_API_KEY','CW_KEY_SECRET'))
    def stop(sig,frame):raise RuntimeError('signal '+str(sig))
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    OUT.mkdir(parents=True,exist_ok=True)
    pins=json.loads((ROOT/'pins.json').read_text())
    deadline=time.monotonic()+3900
    WORK_DEADLINE=deadline
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
        info=json.loads(docker('info','--format','{{json .}}').stdout);assert info['MemoryLimit'] and info['CpuCfsQuota']
        docker('pull',pins['controller_image'],timeout=240)
        REPORT['controller_image_id']=json.loads(docker('image','inspect',pins['controller_image']).stdout)[0]['Id']
        for seconds in (60,300):
            row={'checkout_seconds':seconds,'state':'unstarted'};REPORT['arms'].append(row)
            # Full setup, probe, container creation/copy and teardown allowances.
            allowance=seconds+1560
            if time.monotonic()+allowance>deadline:
                row['reason']='full_arm_allowance_does_not_fit';break
            name=RUN+'-'+str(seconds);directory=OUT/str(seconds);directory.mkdir()
            row.update(state='running',started=time.time())
            created=False
            try:
                docker('create','--name',name,'--cpus=1','--memory=4g','--memory-swap=4g','--network=iris-egress','--label',LABEL,
                       '-w','/work','-e','CHECKOUT_SECONDS='+str(seconds),'-e','DEBIAN_FRONTEND=noninteractive',pins['controller_image'],'sleep','infinity')
                created=True;docker('start',name)
                conf=json.loads(docker('inspect',name).stdout)[0]
                assert conf['HostConfig']['NanoCpus']==1000000000 and conf['HostConfig']['Memory']==4*1024**3
                assert conf['HostConfig']['NetworkMode']=='iris-egress' and not conf['Mounts']
                for f in ('checkout_probe.py','source-pins.json','runner-original.py','runner-candidate.py','auth.py'):
                    docker('cp',str(ROOT/f),name+':/work/'+f,timeout=30)
                # Exact original controller's system acquisition prerequisites;
                # no Harbor, model SDK, repository build or dependency install.
                setup=docker('exec',name,'bash','-c','set -eu; apt-get update; apt-get install -y --no-install-recommends git ca-certificates curl',timeout=300,check=False)
                (directory/'setup.stdout').write_text(setup.stdout);(directory/'setup.stderr').write_text(setup.stderr)
                row['setup_exit']=setup.returncode
                if setup.returncode!=0:raise RuntimeError('Original controller system prerequisites failed')
                total=seconds+840
                result=docker('exec',name,'timeout','--kill-after=15s',str(total),'python','/work/checkout_probe.py',timeout=total+30,check=False)
                row['probe_exit']=result.returncode
                (directory/'probe.stdout').write_text(result.stdout);(directory/'probe.stderr').write_text(result.stderr)
                row['state']='completed'
            except Exception as error:
                row['state']='infrastructure_error';row['error_type']=type(error).__name__;row['error']=str(error)[:400]
            finally:
                CLEANUP=True
                if created:
                    # Kill all git descendants before archiving, even when a
                    # Python/client timeout killed only their immediate parent.
                    stopped=docker('stop','--time','1',name,timeout=30,check=False)
                    row['container_stop_exit']=stopped.returncode
                    copied=docker('cp',name+':/work/evidence/.',str(directory),timeout=60,check=False)
                    row['evidence_copy_exit']=copied.returncode
                    docker('rm','-f',name,timeout=30)
                    row['container_absent']=docker('inspect',name,check=False).returncode!=0
                CLEANUP=False
                row['finished']=time.time()
                (OUT/'progress.json').write_text(json.dumps(REPORT,indent=2)+'\n')
            if row['state']!='completed' or not row.get('container_absent'):
                break
    except Exception as error:
        REPORT['error_type']=type(error).__name__;REPORT['error']=str(error)[:400]
    finally:
        CLEANUP=True
        errors=[]
        if (TOOLS/'docker').exists():
            try:
                ids=docker('ps','-aq','--filter','label='+LABEL).stdout.split()
                if ids:docker('rm','-f',*ids,timeout=120)
                REPORT['owned_containers_absent']=not docker('ps','-aq','--filter','label='+LABEL).stdout.strip()
                # No owned images/volumes are created; the shared base cache is retained.
                REPORT['owned_images_created']=False;REPORT['owned_volumes_created']=False
            except Exception as error:errors.append(type(error).__name__+': '+str(error)[:300])
        try:
            if TOOLS.exists():shutil.rmtree(TOOLS)
        except Exception as error:errors.append(type(error).__name__+': '+str(error)[:300])
        REPORT['cleanup_errors']=errors;REPORT['tools_removed']=not TOOLS.exists();REPORT['finished']=time.time()
        REPORT['output_sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='openms-checkout-result.json'}
        (OUT/'openms-checkout-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
        print('BIOTASKS29_CHECKOUT='+json.dumps(REPORT),flush=True)
    assert REPORT.get('owned_containers_absent') and not errors and not REPORT.get('error')

if __name__=='__main__':main()
