"""Run exactly one native Pi trial per released task, sequentially."""

import asyncio
import hashlib
import json
import os
from pathlib import Path

from harbor.agents.installed.pi import Pi
from harbor.trial.trial import Trial
from harbor_config.models.trial.config import TrialConfig


def write(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + '\n')


async def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    protocol = json.loads(Path('protocol.json').read_text())
    manifest = json.loads(Path('task-manifest.json').read_text())
    for item in manifest['files']:
        path = Path('tasks') / item['task'] / item['path']
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']
    kwargs = protocol['agent_kwargs']
    preflight = Pi(logs_dir=output / 'preflight', model_name=protocol['model'],
                   api_base='https://model.invalid/v1', api_key='not-needed', **kwargs)
    assert preflight._model_limits.context_window == 131072
    assert preflight._model_limits.max_tokens == 32768
    write(output / 'preflight.json', {'context_window': 131072, 'max_output_tokens': 32768,
                                     'thinking': 'medium', 'pi_version': '0.87.0', 'task_hashes_verified': True})
    records = []
    for name in protocol['tasks']:
        judge_env = {}
        if name == 'bix-1-q1':
            judge_env = {'OPENAI_API_KEY': os.environ['JUDGE_PROXY_TOKEN'],
                         'OPENAI_BASE_URL': os.environ['MODEL_PROXY_ROOT'] + '/trial/judge/v1',
                         'MODEL_NAME': protocol['judge']['model']}
        config = TrialConfig.model_validate({
            'task': {'path': str(Path('tasks', name).resolve())},
            'trial_name': name + '-pi-glm53', 'trials_dir': str(output / 'trials'),
            'agent': {'name': 'pi', 'model_name': protocol['model'],
                      'override_setup_timeout_sec': protocol['agent_setup_timeout_sec'],
                      'override_timeout_sec': protocol['agent_timeout_sec'],
                      'kwargs': {**kwargs, 'api_key': 'not-needed',
                                 'api_base': os.environ['MODEL_PROXY_ROOT'] + f'/trial/{name}/v1'}},
            'environment': {'type': 'daytona', 'delete': True,
                            'override_storage_mb': protocol['storage_override_mb'],
                            'kwargs': {'auto_stop_interval_mins': 60, 'auto_delete_interval_mins': 0}},
            'verifier': {'env': judge_env},
            'artifacts': [{'source': '/results', 'destination': 'submitted-results'}] if name.startswith('seta') else
                         [{'source': '/workspace/answer.txt', 'destination': 'answer.txt'}],
        })
        print(json.dumps({'event': 'trial_start', 'task': name}), flush=True)
        try:
            trial = await Trial.create(config)
            result = await trial.run()
            native = result.model_dump(mode='json')
            write(output / f'{name}-result.json', native)
            record = {'task': name, 'rewards': (native.get('verifier_result') or {}).get('rewards'),
                      'exception_info': native.get('exception_info')}
        except Exception as error:
            # Keep infrastructure failures separate; never synthesize zero reward.
            record = {'task': name, 'rewards': None, 'launcher_exception': type(error).__name__}
            write(output / f'{name}-launcher-error.json', {'type': type(error).__name__, 'message': str(error)})
        records.append(record)
        write(output / 'summary.json', {'records': records, 'completed': len(records) == 2})
        print(json.dumps({'event': 'trial_end', 'task': name, 'rewards': record.get('rewards'),
                          'exception_type': (record.get('exception_info') or {}).get('exception_type'),
                          'launcher_exception': record.get('launcher_exception')}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
