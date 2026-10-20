"""Exact admitted native history assets: provider controls, then one blind trial."""

import asyncio
import datetime
import hashlib
import importlib.metadata
import json
import os
import time
from pathlib import Path

from harbor.models.task.task import Task
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial

from glm_solver_settings import ATTEMPT_TIMEOUT_SEC, MODEL
from native_solver_transport import solver_transport_kwargs
from run_pr_provider_preflight import cleanup


def assets(task):
    result = {}
    for file in sorted(task.rglob('*')):
        assert not file.is_symlink(), 'Unexpected linked task asset'
        if file.is_file():
            result[file.relative_to(task).as_posix()] = {
                'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                'mode': oct(file.stat().st_mode & 0o777)}
    return result


def config(task, output, name, provider='continuation_provider_environment'):
    assert provider in {'continuation_provider_environment', 'authored_solver_environment'}
    return TrialConfig.model_validate({
        'task': {'path': str(task.resolve())}, 'trial_name': name,
        'trials_dir': str((output / 'trials').resolve()),
        'agent': {'name': name, 'override_timeout_sec': 900},
        'environment': {
            'import_path': provider + ':RecordedDaytonaEnvironment',
            'delete': True, 'override_cpus': 2, 'override_memory_mb': 4096,
            'override_storage_mb': 10240, 'override_gpus': 0},
    })


async def run():
    assert os.environ['REPO2RLENV_MODEL_WORKER'] == '1'
    assert importlib.metadata.version('harbor') == '0.22.0'
    task = Path('task')
    manifest = json.loads(Path('trial-inputs.json').read_text())
    sdk = json.loads(Path('native-sdk-preflight.json').read_text())
    assert sdk['native_SDK_passed'] and sdk['requests_dispatched'] == sdk['responses_received'] == 1
    assert manifest['route'] in {'pr_runtime/native', 'commit_runtime/native',
                                'repo_reconstruct/swe_flow', 'repo_mutate/swe_smith',
                                'pr_to_env/swe_gen'}
    authored = manifest['route'] in {'repo_reconstruct/swe_flow', 'repo_mutate/swe_smith',
                                    'pr_to_env/swe_gen'}
    if authored:
        assert (manifest['route'], manifest['task_id']) in {
            ('pr_to_env/swe_gen', 'swe-gen-d52d9d8d8c952c886adb'),
            ('repo_mutate/swe_smith', 'swe-smith-2b1ed7afc9535c5c23fb'),
            ('repo_reconstruct/swe_flow', 'swe-flow-3ad7ba60ca7686b2007b'),
            ('repo_mutate/swe_smith', 'swe-smith-53ec5f51639d4053971f'),
            ('repo_mutate/swe_smith', 'swe-smith-f39ded25ef48a6575366')}
    provider = 'authored_solver_environment' if authored else 'continuation_provider_environment'
    assert manifest['blind_attempt_limit'] == 1
    assert manifest['independently_admitted'] is True
    assert assets(task) == manifest['task_assets']
    asset_sha = hashlib.sha256(json.dumps(manifest['task_assets'], sort_keys=True).encode()).hexdigest()
    assert asset_sha == manifest['admitted_asset_manifest_sha256']
    assert not (task / 'environment/docker-compose.yaml').exists()
    checksum = Task(task).checksum
    output = Path(os.environ['IRIS_OUTPUT_DIR']) / 'native-trial'
    output.mkdir(exist_ok=False)
    os.environ['BIOTASKS21_PROVIDER_RECEIPTS'] = str((output / 'provider.jsonl').resolve())
    os.environ['BIOTASKS21_TASK_REPOSITORY'] = manifest['repository']
    os.environ['BIOTASKS21_TASK_ID'] = manifest['task_id']
    state = {'stage': 'new_admission_provider_controls_then_single_blind',
             'task_id': manifest['task_id'], 'task_checksum': checksum,
             'admitted_asset_manifest_sha256': asset_sha,
             'provider_controls': [], 'blind_attempts_started': 0, 'status': 'started',
             'blind_limits': {'timeout_seconds': 900, 'turns': 12, 'max_output_tokens': 2048,
                             'effort': 'unset_native'},
             'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def save():
        (output / 'trial-status.json').write_text(json.dumps(state, indent=2) + '\n')

    save()
    try:
        for agent, expected in [('nop', 0), ('oracle', 1)]:
            assert assets(task) == manifest['task_assets']
            spec = config(task, output, agent, provider)
            trial = await Trial.create(spec)
            result = await asyncio.wait_for(trial.run(), timeout=900)
            row = {'agent': agent, 'expected_reward': expected,
                   'result': result.model_dump(mode='json')}
            state['provider_controls'].append(row)
            save()
            assert result.exception_info is None
            assert result.task_checksum == checksum
            assert result.verifier_result.rewards['reward'] == expected
            cleanup(output)
        assert assets(task) == manifest['task_assets'] and Task(task).checksum == checksum
        assert float(os.environ['BIOTASKS21_INFERENCE_EXPIRES_EPOCH']) - time.time() > 930, 'Insufficient inference-client lifetime; no blind attempt started'
        # The two successful control results were saved before this state.
        state.update(status='blind_attempt_starting', blind_attempts_started=1)
        save()
        token = os.environ['BIOTASKS21_INFERENCE_CLIENT_TOKEN']
        os.environ['OPENAI_API_KEY'] = token
        spec = config(task, output, 'terminus-2', provider)
        spec.trial_name = 'glm-blind-01'
        spec.agent.model_name = MODEL
        spec.agent.kwargs = solver_transport_kwargs(
            os.environ['BIOTASKS21_INFERENCE_CLIENT_URL'].rstrip('/') + '/v1', token)
        spec.agent.override_timeout_sec = ATTEMPT_TIMEOUT_SEC
        trial = await Trial.create(spec)
        result = await asyncio.wait_for(trial.run(), timeout=ATTEMPT_TIMEOUT_SEC)
        assert result.task_checksum == checksum
        state.update(status='blind_completed' if result.exception_info is None else 'blind_trial_failed',
                     blind_result=result.model_dump(mode='json'))
    except BaseException as exc:
        state.update(status='incomplete', error_type=type(exc).__name__)
        raise
    finally:
        try:
            cleanup(output)
        finally:
            state['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save()


if __name__ == '__main__':
    asyncio.run(run())
