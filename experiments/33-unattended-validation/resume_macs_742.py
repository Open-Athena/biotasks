"""Adopt and observe the existing #34 run; never submit or regenerate controls.

Currently implements candidate through verified control readback. Public archive
and cleanup adapters remain explicit pending work, not completed stages.
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
        }.get(stage)

    def probe(self, stage):
        names = self.files(stage)
        if names is None:
            return dict(state='pending', reason='archive/cleanup adapter not yet implemented')
        if all((self.root / name).is_file() for name in names):
            return dict(state='ready', evidence=[dict(path=str(self.root / name),
                sha256=digest(self.root / name)) for name in names])
        if stage == 'remote_terminal':
            gates = [self.root / 'continuation.json', ROOT / 'private/resume-macs-742/observation-gate.json']
            for gate in gates:
                if gate.exists():
                    next_check = json.loads(gate.read_text()).get('next_remote_check_not_before_utc')
                    if next_check and datetime.now(timezone.utc) < datetime.fromisoformat(next_check):
                        return dict(state='pending', reason='bounded observation cadence')
        return dict(state='absent')

    def verify(self, stage, evidence):
        if [item['path'] for item in evidence] != [str(self.root / name) for name in self.files(stage)]:
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
        else:
            raise NotImplementedError(stage)

    def perform(self, stage):
        if stage == 'remote_terminal':
            atomic_write(ROOT / 'private/resume-macs-742/observation-gate.json',
                dict(next_remote_check_not_before_utc=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()))
            command = [self.python, str(self.root / 'collect_macs_742_controls.py'), '--config', self.config]
        elif stage == 'archive_readback_verified':
            command = [self.python, str(self.root / 'harvest_macs_742_controls.py')]
        else:
            raise RuntimeError('Missing pre-existing checkpoint; no regeneration/submission authorized by this adapter')
        subprocess.run(command, check=True, timeout=180)

    def recover(self, stage):
        # Both permitted actions only read the fixed handle/archive and are
        # idempotent; neither creates jobs, containers, model calls or uploads.
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
    atomic_write(state / 'last-step.json', dict(result=result, new_model_calls=0, new_submissions=0))
    print(json.dumps(dict(result=result, new_model_calls=0, new_submissions=0)))


if __name__ == '__main__':
    main()
