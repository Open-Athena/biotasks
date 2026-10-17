"""Offline frozen-parent and dispatch-bound checks; no worker or model calls."""
import copy
import json
from pathlib import Path

from build_dataarc import prepare
from repo2rlenv.spec.input import GenerationInput

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'seeds/pr2633-parent-v1/manifest.json').read_text())
settings = json.loads((root / 'glm-generation-adaptation.json').read_text())
spec = GenerationInput.model_validate({
    'source': {'kind': 'seeds', 'path': str(root / 'seeds/pr2633-parent-v1/parent')},
    'pipeline': {'name': 'terminal_synth', 'recipe': 'dataarc'},
    'llm': {'provider': 'openai', 'model': 'glm-5.3', 'endpoint': 'https://example.invalid/v1',
            'api_key_env': 'FIXTURE_KEY', 'max_concurrent': 1, 'timeout_sec': 1200},
    'execution': {'worker_receipt': '/tmp/fixture-worker.json', 'runtime_wheel': '/tmp/fixture.whl',
                  'campaign_dir': '/tmp/fixture-campaign', 'run_id': 'offline', 'timeout_sec': 6600},
    'output': {'destination': '/tmp/fixture-tasks', 'org': 'open-athena', 'dataset_name': 'fixture'},
})
pipeline, options = prepare(spec, manifest, settings)
assert options.max_candidates == 10 and not pipeline.native_supported
for change in ('hash', 'repairs', 'concurrency', 'timeout'):
    candidate = spec.model_copy(deep=True)
    altered = copy.deepcopy(manifest)
    if change == 'hash':
        altered['recipes']['dataarc']['records'][0]['sha256'] = '0' * 64
    elif change == 'repairs':
        altered['recipes']['dataarc']['options']['max_repairs'] = 3
    elif change == 'concurrency':
        candidate.llm.max_concurrent = 4
    else:
        candidate.execution.timeout_sec = 7200
    try:
        prepare(candidate, altered, settings)
    except ValueError:
        pass
    else:
        raise AssertionError('Accepted changed ' + change)
print('PASS: actual native parent loader identities and rejection of changed seeds, repair bounds, concurrency and deadline; zero live calls.')
