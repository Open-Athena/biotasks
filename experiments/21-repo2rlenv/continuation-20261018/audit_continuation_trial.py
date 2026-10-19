"""Read actual native grades, logs, settings and forwarding usage for a trial."""

import hashlib
import json
import re
from pathlib import Path


def audit(recovered, inputs, inference, cleanup):
    state = json.loads((recovered / 'native-trial/trial-status.json').read_text())
    assert state['status'] == 'blind_completed' and state['blind_attempts_started'] == 1
    manifest = json.loads((inputs / 'trial-inputs.json').read_text())
    assert state['admitted_asset_manifest_sha256'] == manifest['admitted_asset_manifest_sha256']
    assert hashlib.sha256(json.dumps(manifest['task_assets'], sort_keys=True).encode()).hexdigest() == state['admitted_asset_manifest_sha256']
    trials = recovered / 'native-trial/trials'
    cases = []
    for name, expected in [('nop', 0), ('oracle', 1), ('glm-blind-01', 1)]:
        root = trials / name
        result = json.loads((root / 'result.json').read_text())
        details = json.loads((root / 'verifier/reward-details.json').read_text())
        reward = float((root / 'verifier/reward.txt').read_text())
        assert reward == expected == details['reward'] == result['verifier_result']['rewards']['reward']
        assert result['exception_info'] is None and result['task_checksum'] == state['task_checksum']
        assert details['parse_status'] == 'ok' and (details['f2p_total'], details['p2p_total']) == (4, 17)
        assert details['p2p_passed'] == 17 and details['f2p_passed'] == (0 if name == 'nop' else 4)
        statuses = dict(re.findall(r'^(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b',
                                   (root / 'verifier/test_output.log').read_text(), re.M))
        assert len(statuses) == 21
        assert sum(value == 'PASSED' for value in statuses.values()) == (17 if name == 'nop' else 21)
        assert sum(value == 'FAILED' for value in statuses.values()) == (4 if name == 'nop' else 0)
        cases.append({'case': name, 'reward': reward, 'F2P_passed': details['f2p_passed'],
                      'F2P_total': 4, 'P2P_passed': 17, 'P2P_total': 17,
                      'actual_test_statuses_parsed': len(statuses),
                      'result_sha256': hashlib.sha256((root / 'result.json').read_bytes()).hexdigest(),
                      'native_grade_sha256': hashlib.sha256((root / 'verifier/reward-details.json').read_bytes()).hexdigest()})
    spec = json.loads((trials / 'glm-blind-01/config.json').read_text())
    assert spec['agent']['model_name'] == 'openai/glm-5.3'
    assert spec['agent']['override_timeout_sec'] == 900
    kwargs = spec['agent']['kwargs']
    assert kwargs['max_turns'] == 12 and kwargs['llm_call_kwargs']['max_tokens'] == 2048
    assert not any(k in kwargs['llm_call_kwargs'] for k in ('reasoning_effort', 'thinking', 'chat_template_kwargs'))
    result = json.loads((trials / 'glm-blind-01/result.json').read_text())
    trajectory = json.loads((trials / 'glm-blind-01/agent/trajectory.json').read_text())
    completed_steps = [s for s in trajectory['steps'] if s['source'] == 'agent']
    agent_usage = result['agent_result']
    assert len(completed_steps) == agent_usage['metadata']['n_episodes'] == 8
    for key, metric in [('n_input_tokens', 'prompt_tokens'), ('n_output_tokens', 'completion_tokens')]:
        assert sum(s['metrics'][metric] for s in completed_steps) == agent_usage[key]
    calls = [json.loads(line) for line in (inference / 'inference-usage.jsonl').read_text().splitlines()]
    generations = [x for x in calls if x.get('usage')]
    assert len(generations) == 11 and all(x['upstream_status'] == 200 for x in generations)
    assert generations[0]['usage']['prompt_tokens'] == 24 and generations[0]['usage']['completion_tokens'] == 99
    solver_calls = generations[1:]
    assert len(solver_calls) == 10 and all(x['usage']['completion_tokens'] <= 2048 for x in solver_calls)
    totals = {name: sum(x['usage'][key] for x in solver_calls) for name, key in [
        ('input_tokens', 'prompt_tokens'), ('combined_output_tokens', 'completion_tokens')]}
    totals['reported_reasoning_tokens'] = sum(x['usage']['completion_tokens_details']['reasoning_tokens'] for x in solver_calls)
    assert totals['input_tokens'] == agent_usage['n_input_tokens'] + 13055 + 13122
    assert totals['combined_output_tokens'] == agent_usage['n_output_tokens'] + 4096
    providers = [json.loads(line) for line in (recovered / 'native-trial/provider.jsonl').read_text().splitlines()]
    ids = {x['sandbox_id'] for x in providers if x['stage'] == 'created'}
    assert len(ids) == 3 and {x['sandbox_id'] for x in cleanup} == ids
    assert all(x['confirmed_absent'] and x['lookup_http_status'] == 404 for x in cleanup)
    readiness = [x for x in providers if x['stage'] == 'learner_preflight']
    assert len(readiness) == 3 and all(x['network_block_all'] and x['private_paths_and_import_returncode'] == 0 for x in readiness)
    assert len([x for x in providers if x['stage'] == 'native_terminal_setup' and x['session_started']]) == 3
    return {'stage': 'native_provider_controls_and_single_blind_reward_audited',
            'task_id': manifest['task_id'], 'task_checksum': state['task_checksum'],
            'admitted_asset_manifest_sha256': state['admitted_asset_manifest_sha256'],
            'blind_attempts': 1, 'blind_reward': 1, 'native_cases': cases,
            'completed_agent_episodes': 8, 'forwarded_solver_requests': 10,
            'usage_including_native_length_retries': totals,
            'native_agent_reported_usage': {k: agent_usage[k] for k in ('n_input_tokens', 'n_cache_tokens', 'n_output_tokens', 'cost_usd')},
            'limits_verified': {'output_tokens_per_request': 2048, 'agent_turn_limit': 12, 'attempt_timeout_sec': 900, 'effort': 'unset_native'},
            'exact_sandboxes_independently_absent': 3,
            'limitations': ['PR5308 instruction discloses the five-field hash implementation; low-complexity software maintenance.',
                           'Native agent token totals omit two length-truncated responses. Forwarding usage includes both retries in this same blind attempt.',
                           'A single first-attempt reward is not a production success-rate estimate.',
                           'This audits native test correctness, not the deferred end-to-end grader-integrity diagnostic.',
                           'Public credential/route review and durable preservation are separate gates.']}
