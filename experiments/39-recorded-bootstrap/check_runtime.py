"""Offline transport checks; no native runtime or fresh control claim."""
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from budget import Budget
from common import write
from controller import Adapter
from docker_bridge import image_ancestry,tagged_recipe
import supervisor_base
from worker_job import ReplaySupervisor

ROOT=Path(__file__).resolve().parent

class Checks(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='runtime-check-',dir=ROOT/'private');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def test_ancestry_binds_exact_seed(self):
        images={'task':'overlay','overlay':'seed'}
        def inspect(args):return json.dumps([dict(Id=args[-1],Parent=images[args[-1]])]).encode()
        with patch('docker_bridge.subprocess.check_output',side_effect=inspect):
            self.assertEqual(image_ancestry('docker','task','seed'),['task','overlay','seed'])
        for images in [{'task':''},{'task':'task'},{'task':'wrong','wrong':''}]:
            with patch('docker_bridge.subprocess.check_output',side_effect=inspect),self.assertRaises(AssertionError):image_ancestry('docker','task','seed')

    def test_label_is_only_effective_recipe_change(self):
        raw=b'FROM local/r2e-replay/example:abc\nRUN echo hello\n'
        self.assertEqual(tagged_recipe(raw,'fixture').replace(b'LABEL biotasks.run=fixture\n',b''),raw)

    def test_bootstrap_failure_has_no_task_or_controller(self):
        old=json.loads((ROOT.parents[2]/'38/experiments/38-manifest-validation/cohort.json').read_text())
        config=dict(old['families'][0],run_id='fixture',mode='recorded_bootstrap_dependency')
        out=self.root/'out';out.mkdir();write(self.root/'pins.json',json.loads((ROOT/'control-pins.json').read_text()))
        class Fake(ReplaySupervisor):
            def fetch(self,url,path,expected,maximum=0):
                if Path(path).name=='docker.tgz':
                    with tarfile.open(path,'w:gz') as tar:
                        raw=b'fixture';row=tarfile.TarInfo('docker/docker');row.size=len(raw);tar.addfile(row,io.BytesIO(raw))
                else:Path(path).write_bytes(b'fixture')
            def docker(self,*args,**kwargs):
                self.calls.append(args);return subprocess.CompletedProcess(args,1,'','No such image')
            def initialize_dependency(self,deadline):return False
        supervisor=Fake(self.root,out,config);supervisor.calls=[]
        supervisor.work()
        self.assertTrue(all(c[:2]==('image','inspect') for c in supervisor.calls))
        self.assertEqual(supervisor.report['stage'],'bootstrap_initialization_failed')
        self.assertTrue(all(t['state']=='not_attempted_bootstrap_initialization_failure' for t in supervisor.report['tasks']))
        self.assertNotIn('controls_started',supervisor.report)

    def test_unknown_submission_is_observed_never_resubmitted(self):
        adapter=object.__new__(Adapter);adapter.directory=self.root;adapter.family={};adapter.client=object()
        write(self.root/'submission.json',dict(state='submission_pending'))
        with patch('backend.observe',return_value='handle_missing') as observe,patch.object(adapter,'perform') as perform:
            adapter.recover('submission_recorded');observe.assert_called_once();perform.assert_not_called()

    def test_budget_admission_is_bounded_idempotent_and_reconciled(self):
        path=self.root/'budget.json';write(path,dict(events=[],new_paid_capacity_allowed=False,paid_model_execution_enabled=False,
            additional_allocated_cpu_hours=0,outstanding_cpu_hour_reservations=0,additional_reserved_cpu_hour_ceiling=32))
        family=dict(run_id='fixture',source_family_sha256='a'*64,resources=dict(cpus=2,maximum_cpu_hours=5,cleanup_allowance_cpu_hours=1/6))
        budget=Budget(path);budget.admit(family,self.root/'admission.json');budget.admit(family,self.root/'admission.json')
        self.assertEqual(len(json.loads(path.read_text())['events']),2)
        with self.assertRaises(AssertionError):budget.admit(dict(family,run_id='large',resources=dict(family['resources'],maximum_cpu_hours=30)),self.root/'other.json')
        budget.reconcile(dict(job_id='/exedev/fixture',allocated_cpu_hours=1.25));budget.release_cleanup('fixture',dict(verified_empty=True))
        value=json.loads(path.read_text());self.assertEqual(value['additional_allocated_cpu_hours'],1.25);self.assertEqual(value['outstanding_cpu_hour_reservations'],0)
        self.assertEqual(value['events'][0]['child_issue'],39)

    def test_unarchived_evidence_is_preserved(self):
        adapter=object.__new__(Adapter);adapter.directory=self.root;adapter.family=dict(run_id='fixture')
        write(self.root/'readback.json',dict(task_package_verified=False,cleanup=None))
        with patch('backend.submit') as submit:
            with self.assertRaises(AssertionError):adapter.cleanup()
            submit.assert_not_called()

    def test_real_backend_receipt_schema(self):
        # Actual backend.submit preflight is exercised with fake Iris transport;
        # receipt construction and candidate verification are original code.
        import backend
        from types import SimpleNamespace
        class Client:
            def list_jobs(self,**kwargs):return []
        family=dict(run_id='fixture',payload_sha256={'a':'b'},resources={'cpus':2},source_family_sha256='a'*64)
        worker=SimpleNamespace(worker_id='fixture-worker',metadata=SimpleNamespace(tpu_name='reserved',provenance=SimpleNamespace(base_commit='c7c14a252d'),tpu_worker_id=0))
        with patch('backend.choose_worker',return_value=worker):receipt=backend.submit(Client(),family,self.root,{'family.json':b'{}'},self.root/'unused',preflight=True)
        write(self.root/'candidate.json',receipt);write(self.root/'admission.json',dict(source_family_sha256='a'*64))
        adapter=object.__new__(Adapter);adapter.directory=self.root;adapter.family=family
        adapter.verify('candidate_verified',[])
        receipt['job_id']='/exedev/wrong';write(self.root/'candidate.json',receipt)
        with self.assertRaises(AssertionError):adapter.verify('candidate_verified',[])

if __name__=='__main__':unittest.main(verbosity=2)
