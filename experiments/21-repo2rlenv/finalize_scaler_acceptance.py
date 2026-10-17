"""Accept native SCALER fixtures from independent evidence, separately from Marin metadata."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_scaler_exports import audit

ROOT = Path(__file__).resolve().parent


def finalize(campaign, output):
    semantic = audit(campaign, ROOT / 'seeds/scaler-dna-edit-v1/families.json')
    preparation = json.loads((ROOT / 'evidence/scaler-marin-preparation/manifest.json').read_text())
    runtime = json.loads((ROOT / 'evidence/marin-scaler-runtime-01/runtime-result.json').read_text())
    native = json.loads((ROOT / 'evidence/scaler-dna-01/summary.json').read_text())
    output.mkdir(exist_ok=False, parents=True)
    decisions = []
    for semantic_row in semantic['tasks']:
        name = semantic_row['task_id']
        prepared = next(x for x in preparation['tasks'] if x['task'] == name)
        task = campaign / 'tasks' / name
        assets = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(task.rglob('*')) if p.is_file()}
        assert assets == prepared['asset_sha256'], 'Runtime-tested task changed'
        cases = next(x for x in runtime['tasks'] if x['task_id'] == prepared['task_id'])['cases']
        expected = {'equivalent_decimal': 1, 'equivalent_scientific': 1,
                    'wrong_off_by_one': -1, 'invalid_text': -1}
        assert len(cases) == len(expected)
        for case in cases:
            assert case['native_reward'] == case['marin_reward'] == expected[case['case']]
            for route in ('native', 'marin'):
                assert case[route + '_initial_private_paths_absent']
                assert case[route + '_postgrade_private_paths_absent']
        controls = [x for x in native['native_trials'] if x['task_id'] == name.removeprefix('scaler-')]
        assert {(x['agent'], x['reward']) for x in controls} == {('nop', -1), ('oracle', 1)}
        assert all(x['exception_type'] is None and x['command_returncode'] == 0 and
                   x['bundle_hash'] == semantic_row['bundle_hash'] for x in controls)
        decision = {'status': 'accepted_for_bounded_pilot', 'stage': 'independent_native_acceptance',
                    'task_id': prepared['task_id'], 'native_task': name, 'route': 'scaler',
                    'bundle_hash': semantic_row['bundle_hash'], 'native_original_bundle_accepted': True,
                    'asset_sha256': assets, 'independent_reference': semantic_row,
                    'reward': {'range': [-1, 1], 'meaning': 'Exact typed numeric match; incorrect or absent answer is -1.'},
                    'native_controls': {'nop': -1, 'oracle': 1, **expected},
                    'input_provenance': 'Synthetic DNA-alphabet strings; not observed biology.',
                    'split_group': 'scaler-dna-edit-v1', 'independent_family_count': 1,
                    'competency': 'Unit-cost edit distance on a concrete string pair.',
                    'marin_conversion': {'raw_reward_parity': True, 'score_range_metadata_compatible': False,
                        'finding': '../marin-scaler-runtime-01/score-range-diagnosis.json'},
                    'limitations': ['One fixed instance; keep all three instances in one lineage group.',
                        'No claim of broad biological reasoning or biological sequence modeling.',
                        'Marin score-bound metadata remains incompatible; native acceptance does not resolve it.',
                        'Direct solver-provider startup checks and blind attempt remain pending.',
                        'Finite correctness controls do not establish adversarial grader hardening.'],
                    'blind_solver': {'attempts': 0, 'approved_attempts': 1, 'timeout_sec': 900,
                                     'max_turns': 12, 'max_output_tokens': 2048}}
        (output / (name + '.json')).write_text(json.dumps(decision, indent=2) + '\n')
        decisions.append({'task': name, 'status': decision['status'], 'task_id': decision['task_id']})
    return {'accepted_native_tasks': len(decisions), 'independent_families': 1, 'tasks': decisions,
            'blind_attempts': 0, 'model_calls': 0, 'marin_metadata_compatibility': 'unresolved'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = finalize(args.campaign, args.output)
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
