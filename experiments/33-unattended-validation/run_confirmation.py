"""Bounded unattended first submission through archive and owned cleanup.

Use --watch to advance the frozen experiment; restart the same command to resume.
Unknown submission outcomes are observed by their fixed handles, never retried.
"""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import subprocess
import time

from resume_runner import advance, atomic_write, controller_lock, digest

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks34-macs-742-confirm-001'
CLEANUP = 'biotasks34-macs-742-confirm-cleanup-001'
STAGES = ['inputs_verified', 'submission_recorded', 'remote_terminal', 'archive_readback_verified',
    'public_eligibility_reviewed', 'hf_readback_verified', 'cleanup_terminal', 'cleanup_verified']


class Confirmation:
    def __init__(self, experiment, python, config):
        self.source = experiment.resolve()
        self.python = python
        self.config = config
        self.state = ROOT/'private/confirmation-controller'
        self.state.mkdir(parents=True, exist_ok=True)

    def read(self, name):
        return json.loads((self.source/name).read_text())

    def paths(self, stage):
        return {
            'inputs_verified': [self.source/'confirmation-payload-manifest.json'],
            'submission_recorded': [self.source/'run-private'/RUN/'submission.json'],
            'remote_terminal': [self.source/'confirmation-accounting.json'],
            'archive_readback_verified': [self.source/'confirmation-readback.json',
                self.source/'inputs-private/confirmation-output/outputs.tar.zst'],
            'public_eligibility_reviewed': [ROOT/'confirmation-public-review.json', ROOT/'confirmation-evidence-manifest.json'],
            'hf_readback_verified': [ROOT/'confirmation-evidence-receipt.json'],
            'cleanup_terminal': [self.source/'confirmation-cleanup-accounting.json'],
            'cleanup_verified': [self.source/'confirmation-cleanup-readback.json',
                self.source/'inputs-private/confirmation-cleanup-output/outputs.tar.zst'],
        }[stage]

    def gate(self, stage):
        return self.state/(stage+'-next-observation.json')

    def probe(self, stage):
        paths = self.paths(stage)
        if all(p.is_file() for p in paths):
            if stage != 'submission_recorded' or self.read('run-private/'+RUN+'/submission.json')['state'] in ('submitted', 'observed_existing'):
                return dict(state='ready', evidence=[dict(path=str(p), sha256=digest(p)) for p in paths])
        if stage in ('remote_terminal', 'cleanup_terminal') and self.gate(stage).exists():
            gate = json.loads(self.gate(stage).read_text())
            if datetime.now(timezone.utc) < datetime.fromisoformat(gate['not_before']):
                return dict(state='pending')
        return dict(state='absent')

    def verify(self, stage, evidence):
        assert [e['path'] for e in evidence] == [str(p) for p in self.paths(stage)]
        if stage == 'inputs_verified':
            manifest = self.read('confirmation-payload-manifest.json')
            assert manifest['run_id'] == RUN and manifest['model_calls'] == 0
            assert manifest['original_files_verified'] == 10
            for name, expected in manifest['sha256'].items():
                assert digest(self.source/'inputs-private/confirmation-payload'/name) == expected
        elif stage == 'submission_recorded':
            submission = self.read('run-private/'+RUN+'/submission.json')
            assert submission['job_id'] == '/exedev/'+RUN
            assert submission['state'] in ('submitted', 'observed_existing')
            assert submission['model_calls'] == 0 and not submission['new_capacity']
            for name, expected in self.read('confirmation-payload-manifest.json')['sha256'].items():
                assert submission['payload_sha256'][name] == expected
        elif stage in ('remote_terminal', 'cleanup_terminal'):
            name = 'confirmation-accounting.json' if stage == 'remote_terminal' else 'confirmation-cleanup-accounting.json'
            account = self.read(name)
            assert account['job_id'] == '/exedev/'+(RUN if stage == 'remote_terminal' else CLEANUP)
            assert account['state'] in ('succeeded', 'failed') and account['attempts'] == 1
            assert account['model_calls'] == 0
            self.reconcile(account)
        elif stage == 'archive_readback_verified':
            result = self.read('confirmation-readback.json')
            assert result['run_id'] == RUN and result['model_calls'] == result['task_repairs'] == 0
            assert result['archive_sha256'] == self.read('confirmation-accounting.json')['output_archive']['sha256']
            assert digest(self.source/'inputs-private/confirmation-output/outputs.tar.zst') == result['archive_sha256']
            for member in result['archive_members']:
                path = Path(member['path'])
                assert not path.is_absolute() and '..' not in path.parts
                assert digest(self.source/'inputs-private/confirmation-output'/path) == member['sha256']
        elif stage == 'public_eligibility_reviewed':
            from preserve_confirmation import SCOPE
            review = json.loads((ROOT/'confirmation-public-review.json').read_text())
            manifest = json.loads((ROOT/'confirmation-evidence-manifest.json').read_text())
            assert review['public_eligible'] and review['approved_scope'] == manifest['automatic_generation_policy'] == SCOPE
            assert manifest['run_id'] == RUN and manifest['source_issue'] == 34
            assert len(manifest['files']) <= 16 and sum(r['bytes'] for r in manifest['files']) < 4*1024**2
            for row in manifest['files']:
                assert digest(ROOT/'private/confirmation-snapshot'/row['path']) == row['sha256']
        elif stage == 'hf_readback_verified':
            receipt = json.loads((ROOT/'confirmation-evidence-receipt.json').read_text())
            manifest = json.loads((ROOT/'confirmation-evidence-manifest.json').read_text())
            assert receipt['manifest_sha256'] == digest(ROOT/'confirmation-evidence-manifest.json')
            assert receipt['bucket'] == 'open-athena/biotasks' and receipt['anonymous_download_verified']
            assert receipt['overwrites'] is False
            assert receipt['prefix'] == 'research/33-unattended-validation/'+manifest['created_utc'][:10]+'/'+receipt['manifest_sha256']
            expected = {receipt['prefix']+'/'+r['path']:r['sha256'] for r in manifest['files']}
            expected[receipt['prefix']+'/manifest.json'] = receipt['manifest_sha256']
            assert {r['path']:r['sha256'] for r in receipt['objects']} == expected
            assert receipt['verified_objects'] == len(expected)
            # The cleanup submitter consumes the exact verified receipt.
            target = self.source/'confirmation-hf-readback.json'
            if target.exists():
                assert json.loads(target.read_text()) == receipt
            else:
                atomic_write(target, receipt)
        elif stage == 'cleanup_verified':
            result = self.read('confirmation-cleanup-readback.json')
            assert result['archive_sha256'] == self.read('confirmation-cleanup-accounting.json')['output_archive']['sha256']
            assert digest(self.source/'inputs-private/confirmation-cleanup-output/outputs.tar.zst') == result['archive_sha256']
            assert result['result']['verified_empty'] and result['result']['controls']['verified_empty']
            assert result['result']['remaining_images'] == result['result']['remaining_containers'] == []

    def reconcile(self, account):
        with controller_lock(ROOT/'private/budget-update'):
            path = ROOT/'budget.json'
            budget = json.loads(path.read_text())
            run = account['job_id'].removeprefix('/exedev/')
            event = next(e for e in budget['events'] if e.get('run_id') == run)
            if event['state'] == 'terminal reconciled':
                assert event['actual_allocated_cpu_hours'] == account['allocated_cpu_hours']
                return
            assert event['state'] == 'reserved before submission'
            event.update(state='terminal reconciled', actual_allocated_cpu_hours=account['allocated_cpu_hours'])
            admissions = [e for e in budget['events'] if e['kind'] == 'reserved_cpu_admission']
            budget['additional_allocated_cpu_hours'] = sum(e['actual_allocated_cpu_hours'] for e in admissions if e['state'] == 'terminal reconciled')
            budget['outstanding_cpu_hour_reservations'] = sum(e['maximum_allocated_cpu_hours'] for e in admissions if e['state'] == 'reserved before submission')
            atomic_write(path, budget)

    def call(self, filename, *args):
        subprocess.run([self.python, str(filename), *args], check=True, timeout=240)

    def observe(self, stage):
        atomic_write(self.gate(stage), dict(not_before=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
        script = 'collect_confirmation.py' if stage == 'remote_terminal' else 'collect_confirmation_cleanup.py'
        self.call(self.source/script, '--config', self.config)

    def perform(self, stage):
        if stage in ('submission_recorded', 'cleanup_terminal'):
            run = RUN if stage == 'submission_recorded' else CLEANUP
            budget = json.loads((ROOT/'budget.json').read_text())
            assert any(e.get('run_id') == run and e['state'] == 'reserved before submission' for e in budget['events'])
            assert budget['additional_allocated_cpu_hours']+budget['outstanding_cpu_hour_reservations'] <= 32
            script = self.source/('submit_confirmation.py' if stage == 'submission_recorded' else 'submit_confirmation_cleanup.py')
            for action in ('preflight', 'submit'):
                self.call(script, action, '--config', self.config, '--run-id', run)
        elif stage == 'remote_terminal':
            self.observe(stage)
        elif stage == 'archive_readback_verified':
            self.call(self.source/'harvest_confirmation.py')
        elif stage == 'public_eligibility_reviewed':
            self.call(ROOT/'preserve_confirmation.py', 'prepare', '--source', str(self.source))
        elif stage == 'hf_readback_verified':
            self.call(ROOT/'preserve_confirmation.py', 'publish')
        elif stage == 'cleanup_verified':
            self.call(self.source/'harvest_confirmation_cleanup.py')
        else:
            raise RuntimeError('Missing frozen inputs; never regenerate them')

    def recover(self, stage):
        if stage == 'submission_recorded':
            self.call(self.source/'submit_confirmation.py', 'observe', '--config', self.config, '--run-id', RUN)
            submission = self.source/'run-private'/RUN/'submission.json'
            value = json.loads(submission.read_text())
            value['state'] = 'observed_existing'
            atomic_write(submission, value)
        elif stage in ('remote_terminal', 'cleanup_terminal'):
            self.observe(stage)
        else:
            # Fixed archive readback, bounded snapshot preparation or add-only
            # publication; these actions verify existing bytes on recovery.
            self.perform(stage)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', required=True, type=Path)
    parser.add_argument('--python', default='/home/exedev/projects/marin/.venv/bin/python')
    parser.add_argument('--config', default='/home/exedev/projects/marin/lib/iris/config/marin.yaml')
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    adapter = Confirmation(args.experiment, args.python, args.config)
    plan = dict(run_id=RUN, stages=STAGES, model_calls_enabled=False, adopted_existing_submission=False,
        inputs=[dict(path=str(adapter.source/'confirmation-payload-manifest.json'), sha256=digest(adapter.source/'confirmation-payload-manifest.json'))])
    deadline = time.monotonic()+3*3600
    while True:
        result = advance(plan, adapter.state/'journal.json', adapter)
        print(json.dumps(dict(result=result, utc=datetime.now(timezone.utc).isoformat())), flush=True)
        atomic_write(adapter.state/'last-step.json', dict(result=result))
        if result == 'complete' or not args.watch:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError('Controller deadline; resume same journal, never restart a job')
        if result.startswith('waiting:'):
            time.sleep(300)


if __name__ == '__main__':
    main()
