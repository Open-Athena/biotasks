"""Native selected logic, fake process transport: not Docker/daemon evidence."""
import asyncio
import importlib.metadata
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent/'inputs-private/check-dependency/source'))

from tenacity import retry,retry_if_exception_type,stop_after_attempt,wait_exponential
from native_loader import load,sha

ROOT=Path(__file__).resolve().parent


class Process:
    def __init__(self):
        self.finished=asyncio.Event();self.returncode=None;self.terminate_calls=0;self.kill_calls=0;self.cancelled_reads=0
    async def communicate(self):
        try:await self.finished.wait()
        except asyncio.CancelledError:self.cancelled_reads+=1;raise
        return b'fixture output',None
    def terminate(self):self.terminate_calls+=1;self.returncode=-15;self.finished.set()
    def kill(self):self.kill_calls+=1;self.returncode=-9;self.finished.set()


class Checks(unittest.TestCase):
    def setUp(self):
        acquisition=json.loads((ROOT/'package-acquisition.json').read_text())
        assert acquisition['wheel_sha256']=='30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652'
        source=ROOT/'inputs-private/source'
        for row in acquisition['source_files']:assert sha(source/row['path'])==row['sha256']
        self.processes=[];self.namespace=dict(asyncio=asyncio,re=re,ExecResult=SimpleNamespace,
            retry=retry,retry_if_exception_type=retry_if_exception_type,stop_after_attempt=stop_after_attempt,wait_exponential=wait_exponential)
        docker=source/'harbor/environments/docker/docker.py';trial=source/'harbor/trial/trial.py'
        self.loaded=[load(docker,'_sanitize_docker_compose_project_name',self.namespace),
            load(docker,'_run_docker_compose_command',self.namespace,'DockerEnvironment'),
            load(trial,'VerifierTimeoutError',self.namespace),load(trial,'_verify_with_retry',self.namespace,'Trial')]
        self.environment=SimpleNamespace(session_id='fixture',environment_dir=ROOT,
            _docker_compose_paths=[],_env_vars=SimpleNamespace(to_env_dict=lambda **kw:{}),
            _compose_task_env={},_persistent_env={},_windows_container_name=None)

    async def create_process(self,*args,**kwargs):
        self.assertEqual(args[:2],('docker','compose'))
        process=Process();self.processes.append(process);return process

    async def command(self,timeout=None):
        return await self.namespace['_run_docker_compose_command'](self.environment,['exec','main','fixture'],timeout_sec=timeout)

    def test_outer_cancellation_does_not_terminate_process(self):
        async def run():
            with patch('asyncio.create_subprocess_exec',self.create_process):
                with self.assertRaises(asyncio.TimeoutError):await asyncio.wait_for(self.command(),timeout=0.02)
            self.assertEqual(len(self.processes),1)
            process=self.processes[0];self.assertEqual(process.cancelled_reads,1)
            self.assertEqual((process.terminate_calls,process.kill_calls),(0,0));self.assertIsNone(process.returncode)
        asyncio.run(run())

    def test_internal_timeout_does_terminate_process(self):
        async def run():
            with patch('asyncio.create_subprocess_exec',self.create_process):
                with self.assertRaisesRegex(RuntimeError,'Command timed out'):await self.command(timeout=0.02)
            process=self.processes[0];self.assertEqual((process.terminate_calls,process.kill_calls),(1,0))
            self.assertEqual(process.returncode,-15)
        asyncio.run(run())

    def test_native_retry_reuses_environment_without_process_termination(self):
        case=self;verifiers=[]
        class Verifier:
            def __init__(self,task,trial_paths,environment,override_env):
                case.assertIs(environment,case.environment);verifiers.append(self)
            async def verify(self):return await case.command()
        self.namespace['Verifier']=Verifier
        trial=SimpleNamespace(_task=None,_trial_paths=None,_environment=self.environment,
            config=SimpleNamespace(verifier=SimpleNamespace(env={})),result=SimpleNamespace(verifier_result=None),_verifier_timeout_sec=0.02)
        async def run():
            with patch('asyncio.create_subprocess_exec',self.create_process):
                with self.assertRaises(self.namespace['VerifierTimeoutError']):await self.namespace['_verify_with_retry'](trial)
            self.assertEqual(len(verifiers),2);self.assertEqual(len(self.processes),2)
            self.assertTrue(all(p.cancelled_reads==1 and p.terminate_calls==p.kill_calls==0 and p.returncode is None for p in self.processes))
        asyncio.run(run())


def main():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(issue=41,checks_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful(),
        source_wheel_sha256='30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652',
        selected_native_ast_executed=True,process_transport='fake',real_subprocesses_started=0,docker_executed=False,
        limitations='Proves native Python control flow under fake transport; not daemon-side survival, file corruption or historical causation.',
        clients=dict(tenacity=importlib.metadata.version('tenacity')),model_calls=0,remote_jobs=0)
    (ROOT/'cancellation-checks.json').write_text(json.dumps(record,indent=2)+'\n')
    assert result.wasSuccessful()


if __name__=='__main__':main()
