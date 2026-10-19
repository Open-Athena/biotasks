"""Audit actual history-task native controls and blind results, including failures.

Reads frozen inputs and raw evidence only. Passing this audit does not establish
public preservation, endpoint cleanup, complete model usage, or Atlas admission.
"""

import hashlib
import json
import re
from pathlib import Path

from audit_pr_correctness_evidence import assets


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def native_grade(root, f2p, p2p):
    details = json.loads((root / 'verifier/reward-details.json').read_text())
    result = json.loads((root / 'result.json').read_text())
    reward = float((root / 'verifier/reward.txt').read_text())
    assert details['parse_status'] == 'ok' and result['exception_info'] is None
    statuses = dict(re.findall(r'^(\S.*?::.*?)\s+(PASSED|FAILED|ERROR|SKIPPED)\b',
                               (root / 'verifier/test_output.log').read_text(), re.M))
    statuses = {name.removeprefix('./'): status for name, status in statuses.items()}
    assert set(f2p) | set(p2p) <= set(statuses)
    full = sum(statuses[name] == 'PASSED' for name in f2p)
    retained = sum(statuses[name] == 'PASSED' for name in p2p)
    assert (details['f2p_total'], details['p2p_total']) == (len(f2p), len(p2p))
    assert (details['f2p_passed'], details['p2p_passed']) == (full, retained)
    computed = round((full / len(f2p) if f2p else 1) * (retained / len(p2p) if p2p else 1), 6)
    assert reward == computed == details['reward'] == result['verifier_result']['rewards']['reward']
    return {'reward': reward, 'F2P_passed': full, 'F2P_total': len(f2p),
            'P2P_passed': retained, 'P2P_total': len(p2p),
            'actual_native_statuses_parsed': len(statuses),
            'native_command_exit_code': details['exit_code'],
            'native_grade_sha256': file_sha(root / 'verifier/reward-details.json'),
            'original_trial_result_sha256': file_sha(root / 'result.json')}


def audit(recovered, input_root, manifest, checksum_function):
    batch = json.loads((recovered / 'batch-status.json').read_text())
    assert len({x['task_id'] for x in manifest['units']}) == len(manifest['units'])
    observed = {x['task_id']: x for x in batch['units']}
    assert set(observed) <= {x['task_id'] for x in manifest['units']}
    rows = []
    for item in manifest['units']:
        unit = item['unit']
        row = {'task_id': item['task_id'], 'unit': unit, 'blind_attempts': 0,
               'scientific_state': 'not_started', 'Atlas_admitted': False}
        rows.append(row)
        if item['task_id'] not in observed:
            continue
        root = recovered / unit / 'native-trial'
        if not (root / 'trial-status.json').exists():
            row.update(scientific_state='no_task_state_recovered', actual_blind_attempts_unproven=True)
            continue
        state = json.loads((root / 'trial-status.json').read_text())
        inputs = json.loads((input_root / unit / 'trial-inputs.json').read_text())
        task = input_root / unit / 'task'
        actual_assets = assets(task)
        assert actual_assets == inputs['task_assets']
        identity = hashlib.sha256(json.dumps(actual_assets, sort_keys=True).encode()).hexdigest()
        assert identity == item['admitted_asset_manifest_sha256'] == state['admitted_asset_manifest_sha256']
        checksum = checksum_function(task)
        assert checksum == state['task_checksum']
        assert state['blind_attempts_started'] in (0, 1)
        row.update(blind_attempts=state['blind_attempts_started'], task_checksum=checksum,
                   admitted_asset_manifest_sha256=identity, native_stage=state['status'])
        f2p = json.loads((task / 'tests/f2p.json').read_text())
        p2p = json.loads((task / 'tests/p2p.json').read_text())
        controls = []
        for control in state['provider_controls']:
            name = control['agent']
            assert name in {'nop', 'oracle'}
            assert control['result']['task_checksum'] == checksum
            if control['result']['exception_info'] is not None:
                controls.append({'agent': name, 'infrastructure_exception': True})
                continue
            grade = native_grade(root / 'trials' / name, f2p, p2p)
            assert grade['reward'] == control['expected_reward'] == (0 if name == 'nop' else 1)
            controls.append({'agent': name, **grade})
        row['provider_controls'] = controls
        if state['blind_attempts_started'] == 0:
            row['scientific_state'] = 'provider_failed_before_blind_attempt'
            continue
        assert len(controls) == 2 and all('reward' in c for c in controls)
        assert {c['agent']: c['reward'] for c in controls} == {'nop': 0, 'oracle': 1}
        result = state.get('blind_result')
        if not result or result['exception_info'] is not None:
            row['scientific_state'] = 'consumed_blind_attempt_infrastructure_failure_or_incomplete'
            continue
        assert result['task_checksum'] == checksum
        trial = root / 'trials/glm-blind-01'
        spec = json.loads((trial / 'config.json').read_text())
        agent = spec['agent']
        assert agent['model_name'] == 'openai/glm-5.3' and agent['override_timeout_sec'] == 900
        assert agent['kwargs']['max_turns'] == 12 and agent['kwargs']['llm_call_kwargs']['max_tokens'] == 2048
        assert not any(k in agent['kwargs']['llm_call_kwargs'] for k in ('thinking', 'reasoning_effort', 'chat_template_kwargs'))
        grade = native_grade(trial, f2p, p2p)
        original = json.loads((trial / 'result.json').read_text())
        assert original == result
        usage = original['agent_result']
        trajectory = json.loads((trial / 'agent/trajectory.json').read_text())
        steps = [s for s in trajectory['steps'] if s['source'] == 'agent']
        assert len(steps) == usage['metadata']['n_episodes'] <= 12
        for metric, key in [('prompt_tokens', 'n_input_tokens'), ('completion_tokens', 'n_output_tokens')]:
            assert sum(s['metrics'][metric] for s in steps) == usage[key]
        provider = [json.loads(line) for line in (root / 'provider.jsonl').read_text().splitlines()]
        ready = [x for x in provider if x['stage'] == 'learner_preflight']
        assert len(ready) == 3 and all(x['network_block_all'] and x['private_paths_and_import_returncode'] == 0 for x in ready)
        owned = {x['sandbox_id'] for x in provider if x['stage'] == 'created'}
        cleanup = json.loads((root / 'cleanup.json').read_text())
        assert len(owned) == 3 and {x['sandbox_id'] for x in cleanup} == owned
        assert all(x['confirmed_absent'] and x['lookup_http_status'] == 404 for x in cleanup)
        row.update(scientific_state='single_blind_attempt_native_reward_audited', blind_grade=grade,
                   completed_agent_episodes=len(steps), native_agent_reported_usage={
                       k: usage[k] for k in ('n_input_tokens', 'n_output_tokens', 'n_cache_tokens', 'cost_usd')},
                   usage_complete_including_length_retries=False,
                   controller_cleanup_receipts_verified=True, exact_owned_sandbox_ids=sorted(owned))
    return {'stage': 'native_history_batch_results_audited_public_and_independent_cleanup_gates_separate',
            'records': rows, 'blind_attempts_observed': sum(x['blind_attempts'] for x in rows),
            'scored_blind_attempts': sum(x['scientific_state'] == 'single_blind_attempt_native_reward_audited' for x in rows),
            'limits': ['Forwarding-client final usage is needed to count all length-truncated/retried responses.',
                       'Controller cleanup receipts require fresh independent provider lookup.',
                       'No public preservation or Atlas admission is established by this audit.',
                       'Historical task lineages and implementation guidance limit scientific generalization.']}
