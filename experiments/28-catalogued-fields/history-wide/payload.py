"""Assemble unchanged baseline infrastructure plus explicit history-only adaptations."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
BASE_FILES = ['supervisor.py', 'setup_controller.sh', 'harbor_docker.py', 'native_docker.py',
    'cleanup_owned.py', 'run_controls.py', 'observed_cli.py', 'provider_usage.py', 'pins.json']


def build(selected, remaining):
    assert Decimal('0') <= remaining <= Decimal('94.024714')
    baseline = json.loads((BASE / 'input-checkpoint.json').read_text())
    files = {}
    for name in BASE_FILES:
        raw = (BASE / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == baseline['payload_files'][name]['sha256']
        files[name] = raw
    old = '[str(DOCKER), "exec", CONTROLLER, "timeout", "--kill-after=15s", str(seconds), *command]'
    new = '[str(DOCKER), "exec", "-e", "BIOTASKS_NATIVE_DEADLINE_EPOCH=" + str(time.time() + seconds), CONTROLLER, "timeout", "--kill-after=15s", str(seconds), *command]'
    supervisor = files['supervisor.py'].decode(); assert supervisor.count(old) == 1
    files['supervisor.py'] = supervisor.replace(old, new).encode()
    files['run_generation.py'] = (ROOT / 'run_history.py').read_bytes()
    for name in ['history_entry.py', 'discovery_adapter.py', 'cost_guard.py']:
        files[name] = (ROOT / name).read_bytes()
    config = json.loads((BASE / 'native-configs' / (selected['slug'] + '.json')).read_text())
    assert config['repo']['ref'] == selected['ref']
    config['pipeline']['options'] = {'limit': 100}
    config['output']['dataset_name'] = 'biotasks28-history-wide'
    files['native-configs/' + selected['slug'] + '.json'] = (json.dumps(config, indent=2) + '\n').encode()
    identities = ROOT / 'candidate-identities' / (selected['slug'] + '.json')
    checked = json.loads((ROOT / 'inventory-verification.json').read_text())
    expected = next(r for r in checked['repositories'] if r['repo'] == selected['repo'])
    assert hashlib.sha256(identities.read_bytes()).hexdigest() == expected['candidate_id_sha256']
    files['history-identities.json'] = identities.read_bytes()
    budget = {'issue_ceiling_usd': '100', 'baseline_actual_usd': '5.975286',
        'remaining_openrouter_usd': str(remaining), 'per_repository_actual_stop_usd': '5',
        'per_repository_final_call_overshoot_allowed': True,
        'campaign_request_reservation': 'Live maximum listed context/cache-write/completion price, 20% plus $0.10 headroom; one upstream request, num_retries=0, no paid tools. Not a provider-enforced cap.',
        'no_extra_model_calls': True}
    files['history-run-budget.json'] = (json.dumps(budget, indent=2) + '\n').encode()
    return files

