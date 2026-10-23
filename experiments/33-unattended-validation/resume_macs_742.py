"""Adopt and observe the existing #34 run; never submit or regenerate controls.

Public eligibility and budget reservations must be checkpointed before the
corresponding effects. Scientific failure does not prevent evidence preservation.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

from resume_runner import advance, atomic_write, digest

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks34-macs-742-controls-001'


class ExistingControls:
    def __init__(self, experiment, python, config):
        self.root = experiment.resolve()
        self.python = python
        self.config = config

    def read(self, name):
        return json.loads((self.root / name).read_text())

    def files(self, stage):
        return {
            'candidate_verified': ['offline-control-inputs.json', 'offline-export-manifest.json',
                'offline-control-plan.json', 'inputs-private/offline-controls/original-tasks.tar.gz'],
            'submission_recorded': ['controls-submission.json'],
            'remote_terminal': ['macs-742-controls-accounting.json'],
            'archive_readback_verified': ['macs-742-control-results.json',
                'macs-742-controls-result-001.json', 'inputs-private/macs-742-controls-001/outputs.tar.zst'],
            'cleanup_terminal': ['macs-742-image-cleanup-accounting.json'],
            'cleanup_verified': ['macs-742-image-cleanup-readback-001.json',
                'inputs-private/macs-742-image-cleanup-001/outputs.tar.zst'],
        }.get(stage)

    def paths(self, stage):
        if stage == 'public_eligibility_reviewed':
            return [ROOT / 'offline-public-review.json', ROOT / 'offline-evidence-manifest.json']
        if stage == 'hf_readback_verified':
            return [ROOT / 'offline-evidence-receipt.json']
        return [self.root / name for name in self.files(stage)]

    def probe(self, stage):
        paths = self.paths(stage)
        if all(path.is_file() for path in paths):
            return dict(state='ready', evidence=[dict(path=str(path), sha256=digest(path)) for path in paths])
        if stage == 'public_eligibility_reviewed':
            return dict(state='pending', reason='reviewed snapshot must be prepared and checkpointed')
        if stage == 'cleanup_terminal' and not (self.root / 'cleanup-cpu-reservation.json').exists():
            return dict(state='pending', reason='cleanup CPU reservation must be checkpointed')
        if stage in ('remote_terminal', 'cleanup_terminal'):
            gates = [self.root / 'continuation.json', ROOT / 'private/resume-macs-742/observation-gate.json']
            for gate in gates:
                if gate.exists():
                    next_check = json.loads(gate.read_text()).get('next_remote_check_not_before_utc')
                    if next_check and datetime.now(timezone.utc) < datetime.fromisoformat(next_check):
                        return dict(state='pending', reason='bounded observation cadence')
        return dict(state='absent')

    def verify(self, stage, evidence):
        if [item['path'] for item in evidence] != [str(path) for path in self.paths(stage)]:
            raise ValueError('Unexpected evidence inventory')
        if stage == 'candidate_verified':
            inputs = self.read('offline-control-inputs.json')
            manifest = self.read('offline-export-manifest.json')
            assert digest(self.root / 'offline-control-plan.json') == inputs['control_plan_sha256']
            assert digest(self.root / 'offline-export-manifest.json') == inputs['export_manifest_sha256']
            archive = self.root / 'inputs-private/offline-controls/original-tasks.tar.gz'
            assert digest(archive) == inputs['archive_sha256']
            expected = {f['path']: f for f in manifest['task_files']}
            seen = set()
            with tarfile.open(archive, 'r:gz') as tar:
                for member in tar:
                    if member.isdir():
                        continue
                    assert member.isfile() and member.name in expected and member.name not in seen
                    expected_file = expected[member.name]
                    assert member.size == expected_file['bytes'] and member.size < 1024**2
                    assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == expected_file['sha256']
                    seen.add(member.name)
            assert seen == set(expected) and len(seen) == 12
            assert manifest['unchanged_original_files'] == 9
        elif stage == 'submission_recorded':
            submission = self.read('controls-submission.json')
            inputs = self.read('offline-control-inputs.json')
            assert submission['job_id'] == '/exedev/' + RUN and submission['state'] == 'submitted'
            assert submission['model_calls'] == 0 and submission['attempts_allowed'] == 1
            assert submission['payload_sha256']['original-tasks.tar.gz'] == inputs['archive_sha256']
            assert submission['payload_sha256']['control-plan.json'] == inputs['control_plan_sha256']
        elif stage == 'remote_terminal':
            account = self.read('macs-742-controls-accounting.json')
            assert account['job_id'] == '/exedev/' + RUN
            assert account['state'] in ('succeeded', 'failed') and account['attempts'] == 1
            assert account['model_calls'] == 0
        elif stage == 'archive_readback_verified':
            account = self.read('macs-742-controls-accounting.json')
            result = self.read('macs-742-control-results.json')
            raw = self.read('macs-742-controls-result-001.json')
            assert raw['run_id'] == RUN and raw['model_calls'] == 0
            assert result['archive_sha256'] == account['output_archive']['sha256']
            assert digest(self.root / 'inputs-private/macs-742-controls-001/outputs.tar.zst') == result['archive_sha256']
            for member in result['archive_members']:
                path = Path(member['path'])
                assert not path.is_absolute() and '..' not in path.parts
                assert digest(self.root / 'inputs-private/macs-742-controls-001' / path) == member['sha256']
            # Negative scientific outcomes remain valid preserved evidence.
            assert result['model_calls'] == 0
        elif stage == 'public_eligibility_reviewed':
            from preserve_offline_evidence import SCOPE
            review = json.loads((ROOT / 'offline-public-review.json').read_text())
            manifest = json.loads((ROOT / 'offline-evidence-manifest.json').read_text())
            assert review['public_eligible'] is True and review['approved_scope'] == SCOPE
            assert manifest['source_issue'] == 34 and manifest['visibility'] == 'public'
            for row in manifest['files']:
                assert digest(ROOT / 'private/offline-snapshot' / row['path']) == row['sha256']
            assert digest(ROOT / 'offline-public-review.json') == next(r['sha256'] for r in manifest['files'] if r['path'] == 'public-eligibility-review.json')
        elif stage == 'hf_readback_verified':
            receipt = json.loads((ROOT / 'offline-evidence-receipt.json').read_text())
            manifest = json.loads((ROOT / 'offline-evidence-manifest.json').read_text())
            assert receipt['manifest_sha256'] == digest(ROOT / 'offline-evidence-manifest.json')
            assert receipt['anonymous_download_verified'] is True and receipt['overwrites'] is False
            expected = {receipt['prefix'] + '/' + row['path']: row['sha256'] for row in manifest['files']}
            expected[receipt['prefix'] + '/manifest.json'] = receipt['manifest_sha256']
            assert {r['path']: r['sha256'] for r in receipt['objects']} == expected
            assert receipt['verified_objects'] == len(expected)
        elif stage == 'cleanup_terminal':
            account = self.read('macs-742-image-cleanup-accounting.json')
            assert account['job_id'] == '/exedev/biotasks34-macs-742-image-cleanup-001'
            assert account['state'] == 'succeeded' and account['exit_code'] == 0 and account['attempts'] == 1
        elif stage == 'cleanup_verified':
            result = self.read('macs-742-image-cleanup-readback-001.json')
            account = self.read('macs-742-image-cleanup-accounting.json')
            assert result['archive_sha256'] == account['output_archive']['sha256']
            assert digest(self.root / 'inputs-private/macs-742-image-cleanup-001/outputs.tar.zst') == result['archive_sha256']
            assert result['result']['verified_empty'] and result['result']['tools_removed']
            assert result['result']['remaining_images'] == result['result']['remaining_containers'] == []
        else:
            raise NotImplementedError(stage)

    def perform(self, stage):
        if stage == 'remote_terminal':
            atomic_write(ROOT / 'private/resume-macs-742/observation-gate.json',
                dict(next_remote_check_not_before_utc=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()))
            command = [self.python, str(self.root / 'collect_macs_742_controls.py'), '--config', self.config]
        elif stage == 'archive_readback_verified':
            command = [self.python, str(self.root / 'harvest_macs_742_controls.py')]
        elif stage == 'hf_readback_verified':
            command = [self.python, str(ROOT / 'preserve_offline_evidence.py'), 'publish']
        elif stage == 'cleanup_terminal':
            reservation = self.read('cleanup-cpu-reservation.json')
            budget = json.loads((ROOT / 'budget.json').read_text())
            run = 'biotasks34-macs-742-image-cleanup-001'
            assert reservation['run_id'] == run and reservation['maximum_cpu_hours'] == 1 / 6
            assert any(e.get('run_id') == run and e['state'] == 'reserved before submission' for e in budget['events'])
            assert budget['additional_allocated_cpu_hours'] + budget['outstanding_cpu_hour_reservations'] <= budget['additional_reserved_cpu_hour_ceiling']
            base = [self.python, str(self.root / 'submit_macs_742_image_cleanup.py')]
            suffix = ['--config', self.config, '--run-id', run]
            subprocess.run(base + ['preflight'] + suffix, check=True, timeout=180)
            command = base + ['submit'] + suffix
        elif stage == 'cleanup_verified':
            command = [self.python, str(self.root / 'harvest_macs_742_image_cleanup.py')]
        else:
            raise RuntimeError('Missing pre-existing checkpoint; no regeneration/submission authorized by this adapter')
        subprocess.run(command, check=True, timeout=180)

    def recover(self, stage):
        if stage == 'cleanup_terminal':
            # The submit acknowledgement may have been lost. Never resubmit.
            atomic_write(ROOT / 'private/resume-macs-742/observation-gate.json',
                dict(next_remote_check_not_before_utc=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()))
            subprocess.run([self.python, str(self.root / 'collect_macs_742_image_cleanup.py'),
                '--config', self.config], check=True, timeout=180)
        else:
            # Fixed-handle readback or add-only publication with verified reuse.
            self.perform(stage)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', required=True, type=Path)
    parser.add_argument('--python', default='/home/exedev/projects/marin/.venv/bin/python')
    parser.add_argument('--config', default='/home/exedev/projects/marin/lib/iris/config/marin.yaml')
    args = parser.parse_args()
    adapter = ExistingControls(args.experiment, args.python, args.config)
    state = ROOT / 'private/resume-macs-742'
    plan = dict(run_id=RUN, source_checkpoint='1ac199165acc10389655fa8eda65a90c6ccca2ea',
        adopted_existing_submission=True, model_calls_enabled=False,
        inputs=[dict(path=str(adapter.root / name), sha256=digest(adapter.root / name))
            for name in ['offline-control-inputs.json', 'offline-control-plan.json', 'offline-export-manifest.json']])
    result = advance(plan, state / 'journal.json', adapter)
    atomic_write(state / 'last-step.json', dict(result=result, new_model_calls=0, control_submissions=0))
    print(json.dumps(dict(result=result, new_model_calls=0, control_submissions=0)))


if __name__ == '__main__':
    main()
