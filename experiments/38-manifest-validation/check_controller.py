"""Offline regression checks; mocked transport is not native runtime evidence."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import batch_job
from budget import Budget
from collect import pair_flags,parse_control
from common import sha,write
from controller import Adapter
from docker_bridge import tagged_recipe
from evidence import archive_records
import preserve
from preserve import inspect

ROOT=Path(__file__).resolve().parent


class Checks(unittest.TestCase):
    def setUp(self):
        (ROOT/'private').mkdir(exist_ok=True)
        temp=tempfile.TemporaryDirectory(prefix='controller-check-',dir=ROOT/'private');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def budget(self):
        path=self.root/'budget.json'
        write(path,dict(events=[],new_paid_capacity_allowed=False,paid_model_execution_enabled=False,
            additional_allocated_cpu_hours=0,outstanding_cpu_hour_reservations=0,additional_reserved_cpu_hour_ceiling=32))
        family=dict(run_id='fixture',source_family_sha256='a'*64,
            resources=dict(cpus=2,maximum_cpu_hours=2,cleanup_allowance_cpu_hours=1/6))
        return Budget(path),family

    def test_budget_admission_is_idempotent_and_limit_stops(self):
        budget,family=self.budget();budget.admit(family,self.root/'admission.json');budget.admit(family,self.root/'admission.json')
        self.assertEqual(len(json.loads(budget.path.read_text())['events']),2)
        other=dict(family,run_id='too-big',resources=dict(family['resources'],maximum_cpu_hours=31))
        with self.assertRaises(AssertionError):budget.admit(other,self.root/'second.json')
        self.assertEqual(len(json.loads(budget.path.read_text())['events']),2)

    def test_actual_overshoot_is_recorded_before_failure(self):
        budget,family=self.budget();budget.admit(family,self.root/'admission.json')
        with self.assertRaises(AssertionError):budget.reconcile(dict(job_id='/exedev/fixture',allocated_cpu_hours=2.1))
        self.assertEqual(json.loads(budget.path.read_text())['additional_allocated_cpu_hours'],2.1)

    def test_cleanup_release_requires_proof(self):
        budget,family=self.budget();budget.admit(family,self.root/'admission.json')
        with self.assertRaises(AssertionError):budget.release_cleanup('fixture',{})
        budget.release_cleanup('fixture',dict(verified_no_creation=True))
        self.assertEqual(json.loads(budget.path.read_text())['outstanding_cpu_hour_reservations'],2)

    def test_uncertain_submission_only_observed(self):
        adapter=object.__new__(Adapter);adapter.directory=self.root;adapter.family={};adapter.client=object()
        write(self.root/'submission.json',dict(state='submission_pending'))
        with patch('backend.observe',return_value='handle_missing') as observe,patch.object(adapter,'perform') as perform:
            adapter.recover('submission_recorded');observe.assert_called_once();perform.assert_not_called()

    def test_unarchived_volume_never_enters_emergency_deletion(self):
        adapter=object.__new__(Adapter);adapter.directory=self.root;adapter.family=dict(run_id='fixture')
        write(self.root/'readback.json',dict(task_package_verified=False,cleanup=None))
        with patch('backend.submit') as submit:
            with self.assertRaises(AssertionError):adapter.cleanup()
            submit.assert_not_called()

    def test_native_pair_parser_on_archived_cobra_bytes(self):
        # Exact #35 evidence, remapping only its historical jobs-root for this parser fixture.
        archive=ROOT.parents[2]/'35/experiments/35-durable-runtime-artifacts/private/cold-snapshot/evidence/cold-worker.tar.zst'
        manifest=json.loads((archive.parents[3]/'cold-evidence-manifest.json').read_text())
        expected=next(r['sha256'] for r in manifest['files'] if r['path']=='evidence/cold-worker.tar.zst')
        self.assertEqual(sha(archive),expected)
        outer=archive_records(archive,'tar.zst');packed=archive_records(outer['control-artifacts.tar.gz']['data'],'tar.gz')
        task=dict(task='opencobra__cobrapy-1482',expected_f2p=2,expected_p2p=17)
        packed={name.replace('jobs/cobrapy-1482-controls/','jobs/'+task['task']+'/'):row for name,row in packed.items()}
        controls=json.loads(outer['controls/controls.json']['data']);rows=[parse_control(c,task,packed) for c in controls]
        flags=pair_flags(rows,task);self.assertTrue(all(flags.values()))
        for broken in [dict(rows[0],exception={'type':'timeout'}),dict(rows[0],raw_test_logs=[]),dict(rows[0],f2p_total=3)]:
            self.assertFalse(pair_flags([broken,rows[1]],task)['positive_control_pair'])
        forged=copy.deepcopy(controls[0]);forged['trial_results'][0]['result']['exception_info']={'type':'forged'}
        with self.assertRaises(AssertionError):parse_control(forged,task,packed)

    def test_public_archive_scan_rejects_nested_binary_and_secret(self):
        for raw in [b'\x00\x01',b'ghp_'+b'x'*30]:
            buf=io.BytesIO()
            with tarfile.open(fileobj=buf,mode='w:gz') as tar:
                row=tarfile.TarInfo('record.txt');row.size=len(raw);tar.addfile(row,io.BytesIO(raw))
            with self.assertRaises((AssertionError,UnicodeDecodeError)):inspect(buf.getvalue(),'tar.gz')

    def test_partial_publication_recovers_same_bytes_without_overwrite(self):
        # Fake bucket only; this verifies transport recovery and scans, not a live release.
        family=json.loads((ROOT/'runtime-plan.json').read_text())['families'][0]
        source=ROOT.parents[2]/'35/experiments/35-durable-runtime-artifacts/private/cold-snapshot/evidence/cold-worker.tar.zst'
        (self.root/'output').mkdir();(self.root/'output/outputs.tar.zst').write_bytes(source.read_bytes())
        for name in ['submission.json','accounting.json','readback.json']:write(self.root/name,dict(fixture=True))
        preserve.prepare(family,self.root)
        store={};uploads=[];fail=[True]
        class FakeApi:
            def bucket_info(self,bucket):return SimpleNamespace(private=False)
            def list_bucket_tree(self,bucket,prefix,recursive):return [SimpleNamespace(path=k,type='file') for k in store if k.startswith(prefix)]
            def batch_bucket_files(self,bucket,add):
                for path,key in add:
                    assert key not in store;store[key]=Path(path).read_bytes();uploads.append(key)
                    if fail[0]:fail[0]=False;raise TimeoutError('Accepted first object before transport interruption')
            def download_bucket_files(self,bucket,rows,**kwargs):
                assert kwargs['token'] is False
                for key,path in rows:Path(path).write_bytes(store[key])
        with patch('huggingface_hub.HfApi',FakeApi):
            with self.assertRaises(TimeoutError):preserve.publish(self.root)
            receipt=preserve.publish(self.root)
            self.assertTrue(receipt['anonymous_download_verified'])
            self.assertEqual(len(uploads),len(set(uploads)))
            self.assertEqual(preserve.verified_receipt(self.root),receipt)
        self.assertFalse((self.root/'hf-transfer-cache').exists())
        manifest=json.loads((self.root/'manifest.json').read_text());manifest['files'][0]['path']='unreviewed.txt'
        write(self.root/'manifest.json',manifest)
        with self.assertRaises(AssertionError):preserve.verify_stage(self.root)

    def test_only_recipe_change_is_ownership_label(self):
        original=b'FROM python:3.12\nRUN echo hello\n'
        self.assertEqual(tagged_recipe(original,'fixture').replace(b'LABEL biotasks.run=fixture\n',b''),original)

    def supervisor(self,prefix_exit=0,task_exits=(),control_exits=()):
        config=json.loads((ROOT/'cohort.json').read_text())['families'][0]
        config=dict(config,run_id='fixture',tasks=config['tasks'][:2])
        out=self.root/'output';out.mkdir()
        for name in ['pins.json','control-plan.json','setup_controller.sh','run_existing_controls.py','tasks.tar.gz','family.json',
            'bootstrap-prefix.Dockerfile','docker_bridge.py','common.py']:
            source=ROOT/'control-pins.json' if name=='pins.json' else ROOT/name
            (self.root/name).write_bytes(source.read_bytes() if source.exists() else b'placeholder')
        write(self.root/'control-plan.json',config['control_plan'])
        class Fake(batch_job.Supervisor):
            def fetch(self,url,path,expected,maximum=0):
                if Path(path).name=='docker.tgz':
                    with tarfile.open(path,'w:gz') as tar:
                        raw=b'fixture';member=tarfile.TarInfo('docker/docker');member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
                else:Path(path).write_bytes(b'fixture')
            def docker(self,*args,**kwargs):
                self.calls.append(args)
                if args[:2]==('image','inspect'):return subprocess.CompletedProcess(args,1,'','No such image')
                if args[:2]==('volume','inspect'):
                    self.inspects+=1
                    return subprocess.CompletedProcess(args,1 if self.inspects==1 else 0,'[{"Mountpoint":"/fixture"}]','')
                return subprocess.CompletedProcess(args,0,'','')
            def exec_logged(self,name,args,seconds):
                self.logs.append(name)
                code=prefix_exit if name=='bootstrap-build.log' else next(self.task_exits,0) if name.endswith('-build.log') else next(self.control_exits,0) if name.endswith('-controller.log') else 0
                return subprocess.CompletedProcess(args,code)
        supervisor=Fake(self.root,out,config);supervisor.calls=[];supervisor.logs=[];supervisor.inspects=0
        supervisor.task_exits=iter(task_exits);supervisor.control_exits=iter(control_exits)
        return supervisor

    def test_failed_shared_prerequisite_runs_no_controls(self):
        supervisor=self.supervisor(prefix_exit=127)
        with patch('batch_job.unpack_task_archive'):supervisor.work()
        self.assertEqual(supervisor.logs,['bootstrap-build.log'])
        self.assertTrue(all(t['state']=='not_attempted_bootstrap_failure' for t in supervisor.report['tasks']))

    def test_task_build_failure_skips_controls_only_for_that_task(self):
        supervisor=self.supervisor(task_exits=[1,0])
        with patch('batch_job.unpack_task_archive'):supervisor.work()
        self.assertEqual([t['state'] for t in supervisor.report['tasks']],['task_build_failed','controls_attempted'])
        self.assertEqual(sum(n.endswith('-controller.log') for n in supervisor.logs),1)

    def test_wrapper_failure_stops_later_task(self):
        supervisor=self.supervisor(control_exits=[124])
        with patch('batch_job.unpack_task_archive'):supervisor.work()
        self.assertEqual(supervisor.report['tasks'][1]['state'],'not_attempted_prior_wrapper_failure')
        self.assertEqual(sum(n.endswith('-build.log') for n in supervisor.logs),2) # prefix plus first task

    def test_copy_failure_preserves_volume_and_stops_controller(self):
        supervisor=self.supervisor();supervisor.tools.mkdir();(supervisor.tools/'docker').write_text('fixture')
        supervisor.created=True;supervisor.report['resource_creation_started']=True
        supervisor.docker=lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('copy unavailable')) if args[:2]==('exec',supervisor.controller) else subprocess.CompletedProcess(args,0,'','')
        with patch('cleanup_owned.cleanup') as cleanup:supervisor.finish();cleanup.assert_not_called()
        self.assertEqual(supervisor.report['cleanup_deferred']['volume'],'fixture-work')


if __name__=='__main__':unittest.main(verbosity=2)
