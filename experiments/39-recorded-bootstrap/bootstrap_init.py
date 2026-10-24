"""Data-driven original-action initialization; no agent or command repair."""
from collections.abc import Callable
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import urllib.request

from common import content_sha,json_sha,sha,write
from pinned_loader import load_functions,load_post_checks
from recorded_replay import replay_recorded_actions


class Initializer:
    def __init__(self,root,out,docker,owner,deadline):
        self.root=Path(root);self.out=Path(out);self.binary=Path(docker);self.owner=owner;self.deadline=deadline
        self.context=self.root/'replay-context'
        self.docker_config=self.root/'bootstrap-docker-config'
        self.descriptor=json.loads((self.root/'bootstrap-dependency.json').read_text())
        self.report=dict(run_id=owner,started=time.time(),commands_edited=False,model_calls=0,
            descriptor_sha256=sha(self.root/'bootstrap-dependency.json'),source_variant='recorded_bootstrap_dependency')
        self.sequence=0
        self.context_owned=False;self.config_owned=False;self.daemon_creation_attempted=False

    def docker(self,*args,timeout=90,check=True):
        return subprocess.run([str(self.binary),*args],capture_output=True,text=True,timeout=timeout,check=check)

    def save(self):write(self.out/'bootstrap-replay.json',self.report)

    def load_native(self):
        spec=importlib.util.spec_from_file_location('original_docker',self.root/'docker_original.py')
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        return module

    def check_inputs(self):
        d=self.descriptor
        assert os.environ['BIOTASKS_RUN_ID']==self.owner
        assert not any(os.environ.get(k) for k in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN','CW_KEY_SECRET','HF_TOKEN'])
        assert re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',d['repo']) and re.fullmatch('[0-9a-f]{40}',d['bootstrap_ref'])
        assert re.fullmatch(r'[a-z0-9./_-]+@sha256:[0-9a-f]{64}',d['public_base_ref'])
        assert d['dependency_ref'].startswith('local/r2e-replay/') and re.fullmatch(r'[a-z0-9./_:-]+',d['dependency_ref'])
        assert sha(self.root/'recorded-actions.json')==d['actions_sha256']
        assert sha(self.root/'recorded_replay.py')==d['replay_helper_sha256']
        assert sha(self.root/'original-bootstrap.json')==d['original_bootstrap_json_sha256']
        for name,key in [('docker_original.py','bootstrap/docker.py'),('runner_original.py','bootstrap/runner.py'),('auth_original.py','auth.py')]:
            assert sha(self.root/name)==d['native_source_sha256'][key]
        payload=json.loads((self.root/'recorded-actions.json').read_text())
        assert payload['repo']==d['repo'] and payload['ref']==d['bootstrap_ref']
        assert all(a['timeout_seconds']==300 and a['expected_exit_code']!=124 and content_sha(a['command'].encode())==a['command_sha256'] for a in payload['actions'])
        assert not self.context.exists()
        result=self.docker('image','inspect',d['dependency_ref'],check=False)
        assert result.returncode!=0 and 'No such image' in result.stderr, 'Never replace another local dependency'
        self.report.update(inputs_verified=True,actions_sha256=d['actions_sha256'],actions_expected=len(payload['actions']),
            bootstrap_ref=d['bootstrap_ref'],public_base_ref=d['public_base_ref'],dependency_ref=d['dependency_ref'])
        self.save();return payload

    def bounded_run(self,native_run,args,*,timeout=600,input_text=None):
        assert not self.report.get('client_timeout'), 'Only independent teardown after a client timeout'
        assert time.monotonic()+timeout+300<=self.deadline, 'Full original operation plus cleanup reserve must fit'
        assert args[0]=='docker'
        call=list(args)
        if call[1]=='run':
            active=self.docker('ps','-aq','--filter','label=biotasks.run='+self.owner).stdout.split()
            assert not active, 'Only one active bootstrap/fresh sandbox in the two-CPU envelope'
            call[2:2]=['--cpus','1.5','--memory','6g','--memory-swap','6g','--network','iris-egress','--label','biotasks.run='+self.owner]
        result=native_run(call,timeout=timeout,input_text=input_text)
        self.sequence+=1
        row=dict(sequence=self.sequence,docker_operation=args[1],original_command_sha256=json_sha(args),
            effective_command_sha256=json_sha(call),exit_code=result.exit_code,timeout_seconds=timeout,duration_sec=result.duration_sec)
        for stream in ['stdout','stderr']:
            raw=getattr(result,stream).encode();path=self.out/f'call-{self.sequence:03d}-{stream}.txt';path.write_bytes(raw)
            row[stream+'_sha256']=content_sha(raw);row[stream+'_bytes']=len(raw)
        with (self.out/'docker-calls.jsonl').open('a') as target:target.write(json.dumps(row)+'\n')
        if result.exit_code==124:self.report['client_timeout']=True
        return result

    def execute(self):
        self.out.mkdir(parents=True,exist_ok=False)
        original=None;native_run=None;old_path=os.environ.get('PATH','');old_config=os.environ.get('DOCKER_CONFIG');success=False
        try:
            assert not self.docker_config.exists();self.docker_config.mkdir(mode=0o700);self.config_owned=True
            os.environ['DOCKER_CONFIG']=str(self.docker_config)
            payload=self.check_inputs();d=self.descriptor
            os.environ['PATH']=str(self.binary.parent)+':'+old_path
            original=self.load_native()
            native_run=original._run
            bounded=lambda args,**kwargs:self.bounded_run(native_run,args,**kwargs)
            original._run=bounded
            namespace=dict(globals(),logger=logging.getLogger('recorded-bootstrap'),_run=bounded)
            load_functions(self.root/'auth_original.py',{'auth_clone_url'},namespace)
            load_functions(self.root/'runner_original.py',{'BootstrapError','_scrub_token','_run_git_streaming','_shallow_clone_at_ref','_resolve_head_sha','_verify_committed_image'},namespace)
            assert time.monotonic()+900+300<=self.deadline
            self.report['phase']='source_checkout';self.save()
            self.context_owned=True
            namespace['_shallow_clone_at_ref']('https://github.com/'+payload['repo']+'.git',payload['ref'],None,self.context)
            assert namespace['_resolve_head_sha'](self.context)==d['bootstrap_ref']
            self.report['source_commit']=d['bootstrap_ref']
            self.report['phase']='source_sandbox';self.save()
            self.daemon_creation_attempted=True
            sandbox=original.DockerSandbox.start(d['public_base_ref'],self.context,platform='linux/amd64')
            config=json.loads(self.docker('inspect',sandbox.container_id).stdout)[0]
            assert config['Image']==d['expected_base_image_id']
            assert config['HostConfig']['NanoCpus']==1500000000 and config['HostConfig']['Memory']==6*1024**3
            assert config['HostConfig']['NetworkMode']=='iris-egress'
            assert config['Config']['Labels']['biotasks.run']==self.owner
            self.report.update(base_image_id=config['Image'],full_checkout_copy=True,phase='recorded_actions')
            self.save()
            self.report['replay']=replay_recorded_actions(sandbox,payload['actions'],self.out/'actions')
            if self.report['replay']['status']!='matched_recorded_exits':
                self.report['stage']=self.report['replay']['status'];return False
            namespace.update(sandbox=sandbox,outcome=SimpleNamespace(test_cmds=payload['test_cmds']),_emit=lambda *a,**kw:None)
            self.report['phase']='original_smoke_git_checks';self.save()
            load_post_checks(self.root/'runner_original.py',namespace)
            self.report['smoke_passed']=namespace['smoke_ok']
            if not namespace['smoke_ok']:
                self.report['stage']='original_smoke_failed';return False
            # Same commit input and original checker; release its unused source
            # sandbox before starting the independent fresh image container.
            assert self.docker('image','inspect',d['dependency_ref'],check=False).returncode!=0
            self.report['phase']='commit';self.save()
            self.report['image_id']=sandbox.commit(d['dependency_ref'])
            sandbox.cleanup()
            assert not self.docker('ps','-aq','--filter','label=biotasks.run='+self.owner).stdout.split()
            self.report['source_sandbox_removed_before_fresh_check']=True
            self.report['phase']='original_fresh_image_check';self.save()
            self.report['verify_passed'],self.report['verify_detail']=namespace['_verify_committed_image'](d['dependency_ref'],payload['test_cmds'],platform='linux/amd64')
            if not self.report['verify_passed'] or self.report.get('client_timeout'):
                self.report['stage']='original_fresh_check_failed';return False
            image=json.loads(self.docker('image','inspect',d['dependency_ref']).stdout)[0]
            assert image['Id']==self.report['image_id'] and image['Config']['Labels']['biotasks.run']==self.owner
            self.report.update(stage='dependency_verified',image_inspect=dict(Id=image['Id'],RepoDigests=image.get('RepoDigests'),Env=image['Config'].get('Env')))
            success=True
        except Exception as error:
            self.report.update(stage='initialization_error',error_type=type(error).__name__,error=str(error)[:500]);return False
        finally:
            # The original client timeout does not cancel daemon work. This path
            # never passes through the poisoned adapter, and always stops ours.
            if self.daemon_creation_attempted:
                try:
                    ids=self.docker('ps','-aq','--filter','label=biotasks.run='+self.owner).stdout.split()
                    if ids:self.docker('rm','-f',*ids,timeout=120)
                    self.report['bootstrap_containers_removed']=not self.docker('ps','-aq','--filter','label=biotasks.run='+self.owner).stdout.split()
                except Exception as error:self.report['container_cleanup_error']=type(error).__name__+': '+str(error)[:200]
            else:self.report.update(no_daemon_creation_requested=True,bootstrap_containers_removed=False)
            if original is not None and native_run is not None:original._run=native_run
            os.environ['PATH']=old_path
            if old_config is None:os.environ.pop('DOCKER_CONFIG',None)
            else:os.environ['DOCKER_CONFIG']=old_config
            try:
                if self.context_owned and self.context.exists():shutil.rmtree(self.context)
                if self.config_owned and self.docker_config.exists():shutil.rmtree(self.docker_config)
            except Exception as error:self.report['context_cleanup_error']=type(error).__name__+': '+str(error)[:200]
            self.report.update(context_removed=not self.context.exists(),docker_config_removed=not self.docker_config.exists(),finished=time.time())
            if success and not (self.report.get('bootstrap_containers_removed') and self.report['context_removed'] and self.report['docker_config_removed']):
                self.report['stage']='initialization_cleanup_failed';success=False
            self.save()
        return success
