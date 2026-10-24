"""Preflight guards; only the finite writer runs locally, never Docker."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

from artifact_policy import inspect
from collect import event_findings
from common import sha
from worker_job import Diagnostic

ROOT=Path(__file__).resolve().parent


class Checks(unittest.TestCase):
    def test_actual_diagnostic_constructor_accepts_cases_without_tasks(self):
        family=json.loads((ROOT/'runtime-plan.json').read_text())['families'][0]
        config=json.loads((ROOT/family['payload_directory']/'family.json').read_text())
        self.assertNotIn('tasks',config)
        before=copy.deepcopy(config)
        with tempfile.TemporaryDirectory(prefix='constructor-check-',dir=ROOT/'private') as temporary:
            directory=Path(temporary)
            diagnostic=Diagnostic(directory/'uncreated-root',directory/'uncreated-output',config)
            self.assertEqual(list(directory.iterdir()),[])
            self.assertEqual(config,before)
            self.assertEqual(diagnostic.config['cases'],config['cases'])
            self.assertNotIn('tasks',diagnostic.report)
            self.assertFalse(diagnostic.created)
            self.assertEqual(diagnostic.run,family['run_id'])

    def test_real_finite_writer_records_inode_and_complete_events(self):
        (ROOT/'private').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='finite-writer-check-',dir=ROOT/'private') as temporary:
            directory=Path(temporary);log=directory/'writer.log'
            script="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('writer',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.ROOT=Path(sys.argv[2]);m.EVENTS=m.ROOT/'process-events.jsonl';m.main()"
            with log.open('wb') as stream:
                result=subprocess.run([sys.executable,'-c',script,str(ROOT/'fixture_writer.py'),str(directory)],stdout=stream,stderr=subprocess.PIPE,
                    env=dict(os.environ,BIOTASKS_RUN_ID='biotasks41-local-fixturecheck',FIXTURE_WRITER_SECONDS='2'),timeout=5,check=True)
            self.assertEqual(result.stderr,b'')
            raw=log.read_bytes();self.assertEqual(len(raw)%1024,0);self.assertNotIn(b'\0',raw)
            events=[json.loads(line) for line in (directory/'process-events.jsonl').read_bytes().splitlines()]
            finding=event_findings(events,raw);self.assertEqual((finding['writer_starts'],finding['writer_ends']),(1,1))
            self.assertFalse(finding['fixture_mechanism_observed']);self.assertEqual(events[0]['self']['fd1_inode'],log.stat().st_ino)
            self.assertEqual(events[-1]['records']*1024,len(raw))

    def test_survival_requires_live_state_same_pid_start_time_inode_and_offset(self):
        a='a'*32;b='b'*32
        event=dict(event='start',token=b,pid=2,wall_ns=20,self={'fd1_inode':7,'fd1_offset':0},previous=[dict(expected_pid=1,expected_start_ticks=100,expected_token=a,
            observed=dict(pid=1,start_ticks=100,state='S',writer_command=True,fd1_inode=7,fd1_offset=2048))])
        events=[dict(event='start',token=a,pid=1,wall_ns=10,self={'fd1_inode':7,'fd1_offset':0},previous=[]),event,dict(event='sample',token=b,log_nul_bytes=1)]
        raw=(a+':00000000:x\n').encode()+b'\0'+(b+':00000000:x\n').encode()
        self.assertTrue(event_findings(events,raw)['fixture_mechanism_observed'])
        for key,value in [('pid',99),('start_ticks',999),('state','Z'),('writer_command',False),('fd1_inode',8)]:
            broken=copy.deepcopy(events);broken[1]['previous'][0]['observed'][key]=value
            self.assertFalse(event_findings(broken,raw)['fixture_mechanism_observed'],key)
        broken=copy.deepcopy(events);broken[1]['self']['fd1_offset']=1
        self.assertFalse(event_findings(broken,raw)['fixture_mechanism_observed'])
        self.assertFalse(event_findings(events,raw.replace(b'\0',b'x'))['fixture_mechanism_observed'])

    def test_nul_exception_is_exact_path_and_generated_content_only(self):
        policy=json.loads((ROOT/'public-policy.json').read_text());run=policy['run_id'];raw=b'a'*32+b':00000000:xxx\n\0'
        good='jobs/'+run+'-timeout/harbor-timeout-timeout__ABC123/verifier/writer.log'
        self.assertIsNone(inspect(raw,member_path=good))
        for bad in [None,'jobs/unrelated/verifier/writer.log',good.replace('writer.log','other.log'),good.replace('-timeout/','-finite/')]:
            with self.assertRaises(AssertionError):inspect(raw,member_path=bad)
        with self.assertRaises(AssertionError):inspect(raw+b'NOT_FIXTURE_DATA',member_path=good)
        with self.assertRaises(AssertionError):inspect(b'ghp_'+b'x'*30)

    def test_frozen_fixture_resource_and_payload_contract(self):
        plan=json.loads((ROOT/'runtime-plan.json').read_text());family=plan['families'][0]
        allowance=json.loads((ROOT/'retry-allowance.json').read_text())
        self.assertEqual(family['resources']['maximum_cpu_hours']+allowance['prior_actual_cpu_hours'],1)
        payload=ROOT/family['payload_directory']
        for name,digest in family['payload_sha256'].items():self.assertEqual(sha(payload/name),digest)
        config=json.loads((payload/'family.json').read_text())
        for case in config['cases']:
            path=ROOT/'inputs-private/probe/tree/outputs/harbor_timeout'/case['task']/'task.toml'
            value=tomllib.loads(path.read_text());self.assertEqual(value['verifier']['timeout_sec'],5)
            self.assertEqual((value['environment']['cpus'],value['environment']['memory_mb']),(1,6144))
            self.assertFalse(value['environment']['allow_internet']);self.assertTrue(value['environment']['docker_image'].startswith(family['run_id']+'-'))
            import yaml
            compose=yaml.safe_load((path.parent/'environment/docker-compose.yaml').read_text())['services']['main']
            self.assertNotIn('build',compose)
            self.assertEqual(compose['image'],value['environment']['docker_image'])
            self.assertEqual(compose['network_mode'],'none')
        self.assertEqual(config['mode'],'harbor_timeout_diagnostic')


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value=dict(issue=41,checks_run=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),
        local_finite_writer_executed=True,native_docker_executed=False,process_detection_cases='Fixture logic only; not a measured native process-survival result',model_calls=0,
        source_sha256={p.name:sha(p) for p in ROOT.glob('*.py')})
    (ROOT/'probe-checks.json').write_text(json.dumps(value,indent=2)+'\n');assert result.wasSuccessful()


if __name__=='__main__':main()
