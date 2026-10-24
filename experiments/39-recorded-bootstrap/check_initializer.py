"""Original native sandbox/check code with mocked Docker/Git transport only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bootstrap_init
from bootstrap_init import Initializer

ROOT=Path(__file__).resolve().parent


class DockerTransport:
    def __init__(self,descriptor,owner,failure=None):
        self.d=descriptor;self.owner=owner;self.failure=failure;self.active={};self.image=None
        self.calls=[];self.maximum_active=0;self.fresh_started=False;self.original_removed=False
        self.action_calls=0;self.fail_at=6

    def result(self,code=0,stdout='',stderr=''):
        return SimpleNamespace(exit_code=code,stdout=stdout,stderr=stderr,duration_sec=0.01,ok=code==0)

    def run(self,args,**kwargs):
        self.calls.append(list(args));a=list(args[1:])
        if a[0]=='version':return self.result(stdout='25.0.5')
        if a[:2]==['image','inspect']:
            ref=a[2]
            if ref==self.d['public_base_ref']:return self.result(stdout=self.d['expected_base_image_id'])
            if self.image:
                value=dict(Id=self.image,Config=dict(Labels={'biotasks.run':self.owner},Env=['PATH=/usr/local/bin:/usr/bin:/bin']),RepoDigests=[])
                return self.result(stdout=json.dumps(value if '--format' in a else [value]))
            return self.result(1,stderr='Error: No such image')
        if a[0]=='pull':return self.result()
        if a[0]=='run':
            assert a[a.index('--cpus')+1]=='1.5' and a[a.index('--memory')+1]=='6g'
            assert 'biotasks.run='+self.owner in a and a[a.index('--network')+1]=='iris-egress'
            fresh='--rm' in a
            if fresh:
                assert self.original_removed and not self.active
                self.fresh_started=True
            cid='fresh' if fresh else 'source';self.active[cid]=True
            self.maximum_active=max(self.maximum_active,len(self.active))
            if fresh:self.active.pop(cid);return self.result(stdout='synthetic fresh check')
            return self.result(stdout=cid)
        if a[0]=='inspect':
            image_id='sha256:'+'f'*64 if self.failure=='base_identity' else self.d['expected_base_image_id']
            cfg=dict(Image=image_id,HostConfig=dict(NanoCpus=1500000000,Memory=6*1024**3,NetworkMode='iris-egress'),Config=dict(Labels={'biotasks.run':self.owner}))
            return self.result(stdout=json.dumps([cfg]))
        if a[0]=='ps':return self.result(stdout='\n'.join(self.active))
        if a[0]=='cp':
            assert a[1].endswith('/.') and a[2]=='source:/workspace';return self.result()
        if a[0]=='exec':
            if a[2]=='mkdir':return self.result()
            assert a[2:4]==['bash','-lc'];command=a[4]
            if command=='command -v git >/dev/null 2>&1 && echo OK':return self.result(stdout='OK\n')
            self.action_calls+=1
            if self.action_calls==self.fail_at and self.failure in ('divergence','timeout'):
                return self.result(124 if self.failure=='timeout' else 23,stderr='synthetic interruption')
            return self.result(stdout='synthetic original command output')
        if a[0]=='commit':self.image='sha256:'+'a'*64;return self.result(stdout=self.image)
        if a[0]=='rm':
            for cid in a[2:]:self.active.pop(cid,None)
            self.original_removed=True;return self.result()
        raise AssertionError('Unexpected synthetic Docker call: '+repr(a))

    def direct(self,args,check=True,**kwargs):
        result=self.run(['docker',*args]);p=subprocess.CompletedProcess(args,result.exit_code,result.stdout,result.stderr)
        if check:p.check_returncode()
        return p


class InitializerChecks(unittest.TestCase):
    def setUp(self):
        (ROOT/'private').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='initializer-check-',dir=ROOT/'private');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for src,name in [(ROOT/'bootstrap-dependency.json','bootstrap-dependency.json'),
            (ROOT/'inputs-private/recorded-actions.json','recorded-actions.json'),
            (ROOT/'inputs-private/original-bootstrap.json','original-bootstrap.json'),(ROOT/'recorded_replay.py','recorded_replay.py')]:shutil.copyfile(src,self.root/name)
        for source in (ROOT/'inputs-private/native-source').iterdir():shutil.copyfile(source,self.root/source.name)

    def execute(self,failure=None):
        descriptor=json.loads((self.root/'bootstrap-dependency.json').read_text());transport=DockerTransport(descriptor,'fixture',failure)
        class Fixture(Initializer):
            def docker(self,*args,**kwargs):return transport.direct(args,**kwargs)
            def load_native(self):
                original=super().load_native();original._run=transport.run;return original
        instance=Fixture(self.root,self.root/'output',Path('/fixture/docker'),'fixture',time.monotonic()+7800)
        original_loader=bootstrap_init.load_functions
        def loader(path,names,namespace):
            original_loader(path,names,namespace)
            if '_shallow_clone_at_ref' in names:
                def clone(url,ref,token,dest):
                    assert token is None and ref==descriptor['bootstrap_ref'];dest.mkdir()
                namespace['_shallow_clone_at_ref']=clone
                namespace['_resolve_head_sha']=lambda path:descriptor['bootstrap_ref']
        env={k:'' for k in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN','CW_KEY_SECRET','HF_TOKEN']};env['BIOTASKS_RUN_ID']='fixture'
        with patch('bootstrap_init.load_functions',loader),patch.dict(os.environ,env):
            ready=instance.execute()
        return ready,instance.report,transport

    def test_original_sandbox_smoke_and_fresh_sequence(self):
        ready,report,transport=self.execute()
        self.assertTrue(ready);self.assertEqual(report['stage'],'dependency_verified')
        self.assertEqual(report['replay']['status'],'matched_recorded_exits');self.assertEqual(len(report['replay']['steps']),18)
        self.assertTrue(report['source_sandbox_removed_before_fresh_check']);self.assertTrue(transport.fresh_started)
        self.assertEqual(transport.maximum_active,1);self.assertFalse(transport.active);self.assertTrue(report['context_removed'])

    def test_exit_divergence_stops_before_commit_or_fresh(self):
        ready,report,transport=self.execute('divergence')
        self.assertFalse(ready);self.assertEqual(report['stage'],'exit_code_divergence')
        self.assertIsNone(transport.image);self.assertFalse(transport.fresh_started);self.assertFalse(transport.active)
        self.assertEqual(len(report['replay']['steps']),6)

    def test_client_timeout_uses_independent_teardown(self):
        ready,report,transport=self.execute('timeout')
        self.assertFalse(ready);self.assertTrue(report['client_timeout'])
        self.assertEqual(report['stage'],'client_timeout_remove_sandbox');self.assertFalse(transport.active)
        self.assertIsNone(transport.image);self.assertTrue(report['context_removed'])

    def test_wrong_public_base_stops_before_actions(self):
        ready,report,transport=self.execute('base_identity')
        self.assertFalse(ready);self.assertEqual(report['stage'],'initialization_error')
        self.assertNotIn('replay',report);self.assertFalse(transport.active);self.assertIsNone(transport.image)

    def test_preexisting_paths_are_preserved(self):
        for name in ['replay-context','bootstrap-docker-config']:
            path=self.root/name;path.mkdir();(path/'marker').write_text('not created by this initializer')
        ready,report,transport=self.execute()
        self.assertFalse(ready);self.assertFalse(transport.calls)
        for name in ['replay-context','bootstrap-docker-config']:self.assertTrue((self.root/name/'marker').exists())


if __name__=='__main__':unittest.main(verbosity=2)
