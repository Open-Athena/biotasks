"""Small local contract/observer checks; no local Docker or package imports."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from artifact_policy import inspect
from common import sha,write
from observer import SCRIPT
from readback_case import deadline_observations,epoch_ns
from worker_job import Diagnostic

ROOT=Path(__file__).resolve().parent


class Checks(unittest.TestCase):
    def family(self):return json.loads((ROOT/'runtime-plan.json').read_text())['families'][0]

    def test_actual_constructor_has_no_creation_side_effect(self):
        family=self.family();config=json.loads((ROOT/family['payload_directory']/'family.json').read_text());before=copy.deepcopy(config)
        self.assertNotIn('tasks',config)
        with tempfile.TemporaryDirectory(dir=ROOT/'private',prefix='constructor-') as temporary:
            root=Path(temporary);instance=Diagnostic(root/'root',root/'output',config)
            self.assertEqual(list(root.iterdir()),[]);self.assertEqual(config,before)
            self.assertFalse(instance.created);self.assertNotIn('tasks',instance.report)

    def test_payload_and_pair_fixture_identity(self):
        family=self.family();payload=ROOT/family['payload_directory']
        for name,digest in family['payload_sha256'].items():self.assertEqual(sha(payload/name),digest)
        self.assertEqual(family['resources']['maximum_cpu_hours'],2)
        config=json.loads((payload/'family.json').read_text());tree=ROOT/'inputs-private/probe/tree';pairs={}
        for case in config['cases']:
            task=tree/case['task_directory'];value=tomllib.loads((task/'task.toml').read_text())
            self.assertEqual(value['verifier']['timeout_sec'],5);self.assertEqual(value['environment']['cpus'],1)
            self.assertEqual(value['environment']['memory_mb'],6144);self.assertFalse(value['environment']['allow_internet'])
            self.assertEqual(sha(task/'tests/writer.py'),sha(ROOT/'fixture_writer.py'))
            self.assertEqual((task/'tests/test.sh').read_bytes(),b'#!/usr/bin/env bash\nset -eu\npython3 /tests/writer.py > /logs/verifier/writer.log 2>&1\necho 0 > /logs/verifier/reward.txt\n')
            import yaml
            compose=yaml.safe_load((task/'environment/docker-compose.yaml').read_text())['services']['main'];self.assertNotIn('build',compose)
            self.assertEqual(compose['labels']['biotasks.run'],family['run_id']);self.assertEqual(compose['labels']['biotasks.case'],case['id'])
            self.assertTrue(compose['environment']['BIOTASKS_RUN_ID'].startswith('biotasks41-'))
            value['environment'].pop('docker_image');pairs.setdefault(case['name'],[]).append(value)
        for versions in pairs.values():self.assertEqual(versions[0],versions[1])
        self.assertEqual(sha(ROOT/'fixture_writer.py'),sha(ROOT.parents[2]/'41/experiments/41-verifier-cancellation/fixture_writer.py'))

    def test_exact_owned_nul_scope(self):
        owner=self.family()['run_id'];raw=b'a'*32+b':00000000:xxx\n\0';path='jobs/'+owner+'-066-timeout/harbor-timeout-timeout__ABC123/verifier/writer.log'
        self.assertIsNone(inspect(raw,member_path=path))
        for bad in [None,path.replace('-066-','-999-'),path.replace('harbor-timeout-timeout__','harbor-timeout-finite__'),path.replace('writer.log','other.log')]:
            with self.assertRaises(AssertionError):inspect(raw,member_path=bad)
        with self.assertRaises(AssertionError):inspect(raw+b'UNRELATED',member_path=path)
        with self.assertRaises(AssertionError):inspect(b'ghp_'+b'x'*30)

    def test_deadline_identity_and_absence_guards(self):
        trial={'verifier':{'finished_at':'2026-10-24T00:00:05.123456+00:00'}};end=epoch_ns(trial['verifier']['finished_at'])
        self.assertEqual(end,epoch_ns('2026-10-24T01:00:05.123456+01:00'));self.assertEqual(end%1000000000,123456000)
        sample=dict(state='sampled',observed_start_ns=end+1000,observed_finished_ns=end+2000,log_nul_bytes=3,
            processes=[dict(expected_pid=3,expected_start_ticks=100,observed=dict(pid=3,start_ticks=100,state='S',writer_command=True,fd1_inode=7,fd1_offset=100))])
        self.assertTrue(deadline_observations(trial,[sample],[])['live_writer_after_native_verifier_end_observed'])
        for key,value in [('pid',8),('start_ticks',101),('state','Z'),('writer_command',False)]:
            altered=copy.deepcopy(sample);altered['processes'][0]['observed'][key]=value
            result=deadline_observations(trial,[altered],[]);self.assertFalse(result['live_writer_after_native_verifier_end_observed']);self.assertFalse(result['absence_of_live_sample_proves_termination'])
        before=copy.deepcopy(sample);before['observed_start_ns']=end-1;self.assertFalse(deadline_observations(trial,[before],[])['live_writer_after_native_verifier_end_observed'])

    def test_real_read_only_observer_on_finite_child(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'private',prefix='observer-') as temporary:
            directory=Path(temporary);log=directory/'writer.log'
            launcher="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('writer',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.ROOT=Path(sys.argv[2]);m.EVENTS=m.ROOT/'process-events.jsonl';m.main()"
            script=SCRIPT.replace("Path('/logs/verifier')",'Path('+repr(str(directory))+')').replace("Path('/tests/writer.py')",'Path('+repr(str(ROOT/'fixture_writer.py'))+')')
            child=None
            try:
                with log.open('wb') as output:
                    child=subprocess.Popen([sys.executable,'-B','-c',launcher,str(ROOT/'fixture_writer.py'),str(directory)],stdout=output,stderr=subprocess.PIPE,
                        env=dict(os.environ,BIOTASKS_RUN_ID='biotasks41-observer-check',FIXTURE_WRITER_SECONDS='2'))
                    deadline=time.monotonic()+1
                    while not (directory/'process-events.jsonl').exists() or (directory/'process-events.jsonl').stat().st_size==0:
                        self.assertLess(time.monotonic(),deadline);time.sleep(0.02)
                    observed=json.loads(subprocess.check_output([sys.executable,'-B','-c',script],timeout=3));self.assertEqual(observed['state'],'sampled')
                    pid=observed['processes'][0];self.assertEqual(pid['observed']['pid'],child.pid);self.assertEqual(pid['observed']['start_ticks'],pid['expected_start_ticks'])
                    self.assertEqual(pid['observed']['fd1_inode'],log.stat().st_ino);self.assertEqual(observed['log_nul_bytes'],0)
                    child.wait(timeout=4);self.assertEqual(child.returncode,0)
                with log.open('ab') as stream:stream.write(b'\0')
                observed=json.loads(subprocess.check_output([sys.executable,'-B','-c',script],timeout=3));self.assertEqual(observed['log_nul_bytes'],1)
                events=[json.loads(line) for line in (directory/'process-events.jsonl').read_text().splitlines()]
                self.assertEqual([e['event'] for e in events].count('end'),1)
            finally:
                if child and child.poll() is None:child.kill();child.wait(timeout=3)


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    write(ROOT/'probe-checks.json',dict(issue=43,checks_run=result.testsRun,passed=result.wasSuccessful(),errors=len(result.errors),failures=len(result.failures),
        local_finite_writer_and_observer_only=True,local_docker_or_upstream_executed=False,model_calls=0,source_sha256={p.name:sha(p) for p in ROOT.glob('*.py')}))
    assert result.wasSuccessful()


if __name__=='__main__':main()
