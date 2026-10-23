"""Frozen MACS original/rebuild validation; no generation or task repair."""
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import types
import urllib.request

ROOT=Path(__file__).resolve().parent
OWNER='biotasks31-macs-742-native-001'
LABEL_KEY='org.open-athena.biotasks.owner'
TOOLS=ROOT/'native-tools'

def sha(data):return hashlib.sha256(data).hexdigest()

def module(name,path,package=False):
    spec=importlib.util.spec_from_file_location(name,path,submodule_search_locations=[str(path.parent)] if package else None)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value

def load():
    pins=json.loads((ROOT/'macs-native-source-pins.json').read_text())
    for name,digest in pins.items():assert sha((ROOT/name).read_bytes())==digest,name
    for name,path in [('repo2rlenv','upstream'),('repo2rlenv.bootstrap','upstream/bootstrap'),('repo2rlenv.pipelines','upstream/pipelines')]:
        value=types.ModuleType(name);value.__path__=[str(ROOT/path)];sys.modules[name]=value
    executor=module('repo2rlenv.bootstrap.docker',ROOT/'upstream/bootstrap/docker.py')
    parsers=module('repo2rlenv.log_parsers',ROOT/'upstream/log_parsers/__init__.py',True)
    original=module('repo2rlenv.pipelines.pr_runtime_validate',ROOT/'upstream/pipelines/pr_runtime_validate.py')
    module('repo2rlenv.pipelines.runtime_rebuild',ROOT/'candidate/pipelines/runtime_rebuild.py')
    candidate=module('macs_rebuild_validate',ROOT/'candidate/pipelines/pr_runtime_validate.py')
    return executor,parsers,original,candidate

def verify(original,candidate):
    manifest=json.loads((ROOT/'macs-native-742-manifest.json').read_text())
    directory=ROOT/'inputs-private/macs-native-742'
    for name,row in manifest['files'].items():
        data=(directory/name).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    for arm,validator in zip(manifest['arms'],(original,candidate),strict=True):
        kwargs={'rebuild_cmds':manifest['rebuild_cmds']} if arm['name']=='rebuild' else {}
        for side in ('pre','post'):
            params=dict(apply_patch=(directory/'source.patch').read_text() if side=='post' else None,apply_test_patch=(directory/'test.patch').read_text(),test_cmds=manifest['commands'])
            script=validator._build_stage_script(manifest['base_sha'],**params,**kwargs)
            assert script.encode()==(directory/(arm['name']+'-'+side+'.sh')).read_bytes()
            assert sha(script.encode())==arm['stages'][side]['sha256'] and len(script.encode())<128*1024
            if arm['name']=='original':assert candidate._build_stage_script(manifest['base_sha'],**params,rebuild_cmds=None)==script
    return manifest

class ArmTimeout(RuntimeError):pass

class Recorder:
    def __init__(self,sandbox,out,stages,deadline):
        self.sandbox,self.out,self.stages,self.deadline=sandbox,out,stages,deadline;self.calls=[]
    def exec(self,command,*,timeout=300):
        digest=sha(command.encode());stage=next((k for k,v in self.stages.items() if v['sha256']==digest),None)
        if 'echo R2E_START_TEST_OUTPUT' in command:assert stage is not None,'Frozen stage changed'
        if time.monotonic()+timeout+30>self.deadline:raise ArmTimeout('Insufficient remaining allowance for full operation')
        row={'command_sha256':digest,'command_bytes':len(command.encode()),'stage':stage,'timeout':timeout,'started':time.time()};self.calls.append(row)
        try:
            result=self.sandbox.exec(command,timeout=timeout)
            row.update(exit_code=result.exit_code,duration_sec=result.duration_sec)
            for stream in ('stdout','stderr'):
                data=getattr(result,stream).encode();(self.out/f'call-{len(self.calls)-1:02d}-{stream}.txt').write_bytes(data);row[stream+'_sha256']=sha(data)
            if result.exit_code==124:raise ArmTimeout('Client timeout; remove container before further work')
            return result
        except Exception as error:
            row['exception']=type(error).__name__;raise
        finally:
            row['finished']=time.time();(self.out/'calls.json').write_text(json.dumps(self.calls,indent=2)+'\n')

def docker(*args,check=True,timeout=90):
    return subprocess.run([str(TOOLS/'docker'),*args],capture_output=True,text=True,check=check,timeout=timeout)

def setup():
    pins=json.loads((ROOT/'docker-tool.json').read_text());TOOLS.mkdir()
    archive=TOOLS/'docker.tgz'
    with urllib.request.urlopen(pins['docker_url'],timeout=60) as src,archive.open('wb') as dst:
        size=0
        while chunk:=src.read(1024*1024):
            size+=len(chunk);assert size<100*1024**2;dst.write(chunk)
    assert sha(archive.read_bytes())==pins['docker_sha256']
    with tarfile.open(archive) as tar:(TOOLS/'docker').write_bytes(tar.extractfile('docker/docker').read())
    (TOOLS/'docker').chmod(0o755);archive.unlink();os.environ['PATH']=str(TOOLS)+':'+os.environ['PATH']

def interrupted(sig,frame):raise RuntimeError('Signal '+str(sig))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    executor,parsers,original,candidate=load();manifest=verify(original,candidate)
    if args.check:
        assert parsers.parse_logs(['python -m pytest -v'],'test/test_a.py::test_a PASSED [100%]\n')=={'test/test_a.py::test_a':'PASSED'}
        print(json.dumps({'frozen_stage_scripts':4,'default_off_parity':True,'source_hashes_verified':True,'parser_dispatch':True,'docker_execution':False}));return
    assert os.environ.get('BIOTASKS_RUN_ID')==OWNER
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    out=Path(os.environ['IRIS_OUTPUT_DIR']);out.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+5700;label=LABEL_KEY+'='+OWNER
    report={'run_id':OWNER,'model_calls':0,'new_capacity':False,'transport':'original argv','arms':[],'started':time.time(),'image_id':manifest['image_id']}
    try:
        setup()
        info=json.loads(docker('info','--format','{{json .}}').stdout);assert info['MemoryLimit'] and info['CpuCfsQuota']
        image=json.loads(docker('image','inspect',manifest['image_tag']).stdout)[0]
        assert image['Id']==manifest['image_id'] and image['Config']['Labels'][LABEL_KEY]==manifest['image_owner']
        assert not docker('ps','-aq','--filter','label='+label).stdout.strip()
        for arm,validator in zip(manifest['arms'],(original,candidate),strict=True):
            record={'name':arm['name'],'started':time.time(),'state':'unstarted'};report['arms'].append(record)
            # <=3180s upstream worst-case operation time, plus container/archive margin.
            if deadline-time.monotonic()<3300:
                record['reason']='Full arm allowance unavailable';continue
            dest=out/arm['name'];dest.mkdir();cid=None;recorder=None
            try:
                cid=docker('run','-d','--label',label,'--cpus=1.5','--memory=6g','--memory-swap=6g','--pids-limit=512','--network=iris-egress','--entrypoint=/bin/bash',manifest['image_id'],'-c','sleep 5800').stdout.strip()
                assert cid and all(c in '0123456789abcdef' for c in cid)
                recorder=Recorder(executor.DockerSandbox(cid,'/workspace','linux/amd64'),dest,arm['stages'],deadline)
                directory=ROOT/'inputs-private/macs-native-742'
                kwargs={'rebuild_cmds':manifest['rebuild_cmds']} if arm['name']=='rebuild' else {}
                outcome=validator.validate_pr(sandbox=recorder,base_commit=manifest['base_sha'],patch=(directory/'source.patch').read_text(),test_patch=(directory/'test.patch').read_text(),test_cmds=manifest['commands'],language='python',timeout=600,**kwargs)
                (dest/'outcome.json').write_text(json.dumps(dataclasses.asdict(outcome),indent=2)+'\n')
                record.update(state='completed',status=outcome.status,reason=outcome.reason,f2p_count=len(outcome.fail_to_pass),p2p_count=len(outcome.pass_to_pass))
            except ArmTimeout as error:record.update(state='censored_timeout',reason=str(error))
            except Exception as error:record.update(state='exception',exception=type(error).__name__,reason=str(error)[:500])
            finally:
                if cid:
                    detail=json.loads(docker('inspect',cid).stdout)[0];assert detail['Config']['Labels'][LABEL_KEY]==OWNER
                    docker('rm','-f',cid);assert docker('inspect',cid,check=False).returncode!=0;record['container_removed']=True
                record['calls']=recorder.calls if recorder else [];record['finished']=time.time()
                (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    except Exception as error:report.update(error=type(error).__name__,reason=str(error)[:500])
    finally:
        errors=[]
        if (TOOLS/'docker').exists():
            try:
                ids=docker('ps','-aq','--filter','label='+label).stdout.split()
                if ids:docker('rm','-f',*ids,timeout=120)
                report['owned_containers_absent']=not docker('ps','-aq','--filter','label='+label).stdout.strip()
                report['retained_image']=manifest['image_tag']
            except Exception as error:errors.append(type(error).__name__)
        if TOOLS.exists():shutil.rmtree(TOOLS)
        report.update(cleanup_errors=errors,tools_removed=not TOOLS.exists(),finished=time.time())
        report['output_sha256']={str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='comparison.json'}
        (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        print('BIOTASKS31_NATIVE='+json.dumps(report),flush=True)
    assert report.get('owned_containers_absent') and not errors and 'error' not in report

if __name__=='__main__':main()
