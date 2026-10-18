"""No-model direct-Daytona Harbor controls for the accepted PR2633 profile."""
import argparse
import asyncio
import hashlib
import json
import os
import time
from importlib.metadata import version
from pathlib import Path

from daytona import Daytona
from daytona.common.errors import DaytonaNotFoundError, DaytonaConflictError
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from preserve_author_output import preserve


def check_task(task, acceptance):
    decision = json.loads(acceptance.read_text())
    assert decision['status'] == 'accepted_for_bounded_pilot'
    runtime_path = os.environ.get('BIOTASKS21_RUNTIME_MANIFEST')
    runtime = json.loads(Path(runtime_path).read_text()) if runtime_path else None
    if runtime:
        assert runtime['changed_assets'] == ['environment/Dockerfile']
        assert runtime['task_id'] == decision['task_id']
        assert set(runtime['asset_sha256']) == set(decision['asset_sha256'])
        expected_append = ('\n# Solver runtime tooling: installed at build time; learner remains offline.\n'
                           'RUN apt-get update && apt-get install -y --no-install-recommends tmux && rm -rf /var/lib/apt/lists/* \\\n'
                           '    && tmux -V > /opt/terminus-tool-version.txt\n')
        assert runtime['dockerfile_append'] == expected_append
    for name, digest in decision['asset_sha256'].items():
        data = (task / name).read_bytes()
        if runtime:
            assert hashlib.sha256(data).hexdigest() == runtime['asset_sha256'][name], name
            if name == 'environment/Dockerfile':
                suffix = expected_append.encode()
                assert data.endswith(suffix)
                data = data[:-len(suffix)]
        assert hashlib.sha256(data).hexdigest() == digest, name
    assert not (task / 'environment/docker-compose.yaml').exists()


def config(task, output, agent):
    provider = os.environ.get('BIOTASKS21_PROVIDER_MODULE', 'pr_provider_environment')
    if provider not in {'pr_provider_environment', 'lcc_provider_environment', 'scaler_provider_environment', 'history_provider_environment', 'alpha_provider_environment'}:
        raise ValueError('Unreviewed provider module')
    return TrialConfig.model_validate({
        'task': {'path': str(task.resolve())}, 'trial_name': agent,
        'trials_dir': str((output / 'trials').resolve()),
        'agent': {'name': agent, 'override_timeout_sec': 900},
        'environment': {'import_path': provider + ':RecordedDaytonaEnvironment',
                        'delete': True, 'override_cpus': 2, 'override_memory_mb': 4096,
                        'override_storage_mb': 10240, 'override_gpus': 0},
    })


def cleanup(output):
    path = output / 'provider.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    ids = {row['sandbox_id'] for row in records if 'sandbox_id' in row}
    client = Daytona()
    receipts = []
    for identity in sorted(ids):
        item = {'sandbox_id': identity, 'confirmed_absent': False,
                'delete_conflicts': 0}
        receipts.append(item)
        deadline = time.monotonic() + 180
        try:
            while time.monotonic() < deadline:
                try:
                    sandbox = client.get(identity)
                except DaytonaNotFoundError:
                    item.update(confirmed_absent=True, lookup_http_status=404)
                    break
                if not item.get('additional_delete_requested'):
                    try:
                        client.delete(sandbox, timeout=max(1, int(deadline-time.monotonic())))
                        item['additional_delete_requested'] = True
                    except DaytonaNotFoundError:
                        # Confirm with a separate lookup on the next iteration.
                        pass
                    except DaytonaConflictError:
                        # Harbor may already have initiated asynchronous deletion.
                        item['delete_conflicts'] += 1
                time.sleep(min(5, max(0, deadline-time.monotonic())))
            if not item['confirmed_absent']:
                raise TimeoutError('Owned sandbox deletion was not confirmed within 180 seconds')
        finally:
            (output / 'cleanup.json').write_text(json.dumps(receipts, indent=2) + '\n')
    assert all(item['confirmed_absent'] for item in receipts)
    requested = {row['environment_name'] for row in records if row.get('stage') == 'create_requested'}
    created = {row['environment_name'] for row in records if row.get('stage') == 'created'}
    assert requested <= created, 'Uncertain creation requires provider reconciliation'


async def run(args, *, validate_task=check_task):
    assert os.environ.get('REPO2RLENV_MODEL_WORKER') == '1'
    assert version('harbor') == '0.22.0'
    validate_task(args.task, args.acceptance)
    bounds = json.loads(args.acceptance.read_text())['reward']['range']
    assert bounds in ([0, 1], [-1, 1]), 'Unexpected accepted reward range'
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['BIOTASKS21_PROVIDER_RECEIPTS'] = str((args.output / 'provider.jsonl').resolve())
    state = {'stage': 'no_model_provider_controls', 'model_calls': 0, 'cases': [], 'status': 'running'}
    deadline = time.monotonic() + int(os.environ['BIOTASKS21_PREFLIGHT_REMAINING_SEC'])
    try:
        for agent in args.agents:
            expected = {'nop': bounds[0], 'oracle': bounds[1]}[agent]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Compatibility probe deadline reached')
            trial = await Trial.create(config(args.task, args.output, agent))
            result = await asyncio.wait_for(trial.run(), timeout=min(900, remaining))
            row = {'agent': agent, 'expected_reward': expected,
                   'result': result.model_dump(mode='json')}
            state['cases'].append(row)
            (args.output / 'status.json').write_text(json.dumps(state, indent=2) + '\n')
            assert result.exception_info is None, 'Native trial failed'
            assert result.verifier_result is not None
            assert result.verifier_result.rewards['reward'] == expected
            # Confirm each environment was deleted before starting another.
            cleanup(args.output)
        state['status'] = 'passed'
    except BaseException as exc:
        state.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        try:
            cleanup(args.output)
        finally:
            (args.output / 'status.json').write_text(json.dumps(state, indent=2) + '\n')
            preserve(args.output, Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('task', 'acceptance', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--agents', nargs='+', choices=['nop', 'oracle'], default=['nop', 'oracle'])
    asyncio.run(run(parser.parse_args()))
