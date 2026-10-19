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

continued = copy.deepcopy(manifest)
consumed = [manifest['recipes']['dataarc']['records'][0]['sha256']]
continued['continuation_bounds'] = {
    'campaign_candidate_cap': 10, 'campaign_target': 3,
    'prior_charged_candidates': 1, 'prior_independent_admissions': 0,
    'this_run_max_candidates': 1, 'consumed_seed_sha256': consumed,
}
continued['recipes']['dataarc']['options'].update(
    target=1, max_candidates=1, exclude_seed_sha256=consumed)
_, options = prepare(spec, continued, settings)
assert options.max_candidates + continued['continuation_bounds']['prior_charged_candidates'] <= 10
for change in ('recharge_consumed', 'overrun', 'reset_prior', 'unknown_seed'):
    altered = copy.deepcopy(continued)
    if change == 'recharge_consumed':
        altered['recipes']['dataarc']['options']['exclude_seed_sha256'] = []
    elif change == 'overrun':
        altered['continuation_bounds']['this_run_max_candidates'] = 10
        altered['recipes']['dataarc']['options']['max_candidates'] = 10
    elif change == 'reset_prior':
        altered['continuation_bounds']['prior_charged_candidates'] = 0
    else:
        altered['continuation_bounds']['consumed_seed_sha256'] = ['0' * 64]
        altered['recipes']['dataarc']['options']['exclude_seed_sha256'] = ['0' * 64]
    try:
        prepare(spec, altered, settings)
    except ValueError:
        pass
    else:
        raise AssertionError('Accepted invalid continuation ' + change)
print('PASS: actual native parent loader identities and rejection of changed seeds, repair bounds, concurrency and deadline; zero live calls.')
print('PASS: bounded continuation accepts existing pool, excludes consumed IDs and rejects recharging, cap overruns and counter resets.')
