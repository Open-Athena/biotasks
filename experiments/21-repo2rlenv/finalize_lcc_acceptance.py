"""Reconcile the exact LCC assets with recorded correctness and runtime evidence."""
import hashlib
import json
import tomllib
from pathlib import Path

from audit_lcc_acceptance import audit

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def finalize(task, conversion_path):
    evidence = ROOT / 'evidence'
    prior = audit(task, evidence)
    conversion = json.loads(conversion_path.read_text())
    summary = json.loads((evidence / 'lcc-marin-preparation/conversion-summary.json').read_text())
    assert sha(conversion_path) == summary['full_conversion_report_sha256']
    manifest = conversion['native_asset_manifest']
    assert hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest() == summary['native_asset_manifest_sha256']
    for row in manifest:
        path = task / row['path']
        assert not path.is_symlink()
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
    assert {str(p.relative_to(task)) for p in task.rglob('*') if p.is_file()} == {r['path'] for r in manifest}
    config = tomllib.loads((task / 'task.toml').read_text())
    contract = json.loads((task / 'tests/contract.json').read_text())
    assert config['verifier']['environment_mode'] == 'separate'
    assert config['agent']['user'] == 'learner'
    assert config['agent']['network_mode'] == config['verifier']['network_mode'] == 'no-network'
    run_path = evidence / 'marin-lcc-runtime-02/runtime-result.json'
    runtime = json.loads(run_path.read_text())
    assert runtime['status'] == 'native_marin_lcc_parity_passed'
    expected = {'baseline': 0, 'reference': 1, 'partial_dna_only': 0,
                'equivalent_dna_entropy_preserve_legacy': 1,
                'wrong_constant_zero': 0, 'wrong_whole_sequence': 0}
    assert {c['case'] for c in runtime['cases']} == set(expected)
    for case in runtime['cases']:
        assert case['native_reward'] == case['marin_reward'] == expected[case['case']]
        assert set(case['native_details']['statuses']) == set(contract['expected_passes'])
        assert case['marin_result']['status'] == 'graded'
        for route in ('native', 'marin'):
            assert case[route + '_initial_import'] == '1.89.dev0'
            assert case[route + '_initial_private_paths_absent']
            assert case[route + '_postgrade_private_paths_absent']
    schema = json.loads((run_path.parent / 'schema-result.json').read_text())
    assert schema['task_id'] == summary['task_id']
    assert schema['marin_revision'] == summary['marin_revision']
    assert schema['worker_resources'] == 0 and schema['native_reward_preserved_in_spec']
    assert json.loads((run_path.parent / 'cleanup-verification.json').read_text())['result'] == 'sandbox_absent'
    return {
        'status': 'accepted_for_bounded_pilot', 'stage': 'independent_acceptance',
        'task_id': summary['task_id'], 'repository': 'Biopython', 'route': 'swe_smith',
        'profile': 'explicit_full_source_build_with_separate_verifier',
        'native_original_bundle_accepted': False,
        'bundle_identity': prior['bundle_identity'],
        'exact_runtime_asset_manifest_sha256': summary['native_asset_manifest_sha256'],
        'profile_interventions': ['Recorded full source build contexts, editable install and required GenBank fixture',
                                  'Regular LICENSE bytes replacing source symlink',
                                  'Preinstalled tmux for terminal solver'],
        'scope': 'Repair a synthetic constant mutation in local sequence-composition complexity while preserving native regression tests.',
        'inputs': 'Synthetic code mutation and supplied DNA example; not observed biological measurements.',
        'competencies': ['Python debugging', 'Sliding-window composition entropy', 'Scientific-library regression preservation'],
        'reward': {'kind': 'native_binary_all_expected_tests_pass', 'range': [0, 1], 'tests': len(contract['expected_passes'])},
        'gates': {'prompt_arithmetic': prior['prompt_arithmetic'], 'full_partial_incorrect': expected,
                  'repeatability': prior['existing_controls'], 'runtime_parity': str(run_path.relative_to(ROOT)),
                  'exact_runtime_assets_verified': len(manifest), 'separate_verifier': True},
        'asset_sha256': summary['key_asset_hashes'],
        'limitations': prior['limitations'] + ['Acceptance applies only to the recorded adapted runtime profile.',
            'Base-image tags and package indexes remain rebuild dependencies.',
            'Public image publication, Atlas admission and training readiness are separate.',
            'A direct-provider terminal startup check remains required before a blind attempt.'],
        'blind_solver': {'attempts': 0, 'approved_attempts': 1, 'timeout_sec': 900,
                         'max_turns': 12, 'max_output_tokens': 2048},
        'model_calls': 0,
    }
