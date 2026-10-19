"""Audit recovered controls against frozen inputs and original native assets.

This reads evidence only. It does not run target code or infer publication,
blind-solver completion, Atlas admission, or end-to-end grader security.
"""
import argparse
import hashlib
import json
import tomllib
from pathlib import Path


def assets(root, exclude=()):
    records = {}
    for file in sorted(root.rglob('*')):
        assert not file.is_symlink(), 'Linked task asset'
        relative = file.relative_to(root).as_posix()
        if file.is_file() and relative not in exclude:
            records[relative] = {'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'mode': oct(file.stat().st_mode & 0o777)}
    return records


def audit(evidence, manifest, source_roots, *, allow_failed_controls=False):
    from audit_history_blind_batch import native_grade

    summary = json.loads((evidence / 'summary.json').read_text())
    assert len(summary['records']) == len(manifest['tasks'])
    records = []
    for item in manifest['tasks']:
        pr = item['pr']
        row = next(x for x in summary['records'] if x['pr'] == pr)
        root = evidence / f'pr{pr}'
        task = root / 'portable/task'
        original = source_roots[item['repository_key']] / item['task_member']
        profile = json.loads((root / 'portable/profile.json').read_text())
        assert assets(original) == profile['source_assets']
        actual = assets(task)
        assert actual == profile['portable_assets']
        sha = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
        assert sha == item['portable_asset_manifest_sha256'] == row['profile_asset_sha256']
        changed = {'environment/Dockerfile', 'environment/docker-compose.yaml', 'task.toml'}
        assert assets(original, changed) == assets(task, changed)
        config = tomllib.loads((task / 'task.toml').read_text())
        assert all(config[phase]['network_mode'] == 'no-network' for phase in ('environment', 'agent', 'verifier'))
        assert config['environment']['cpus'] == 1 and config['environment']['memory_mb'] == 2048
        assert config['agent']['timeout_sec'] == 900
        assert not (task / 'environment/docker-compose.yaml').exists()
        docker = (task / 'environment/Dockerfile').read_text()
        assert 'tmux -V > /opt/terminus-tool-version.txt' in docker
        assert not any(line.lstrip().upper().startswith(('COPY ', 'ADD ')) for line in docker.splitlines())
        cases = []
        expected = {'baseline': 0, 'native_reference': 1, 'alternative': 1, 'partial': 'fractional', 'incorrect': 0, 'alternative_repeat': 1}
        if pr == 2624:
            expected['partial'] = 0
        f2p = json.loads((task / 'tests/f2p.json').read_text())
        p2p = json.loads((task / 'tests/p2p.json').read_text())
        assert {x['case'] for x in row['cases']} == set(expected) and len(row['cases']) == 6
        for case in row['cases']:
            name = case['case']
            bundle = root / 'controls' / name
            assert assets(bundle, {'solution/solve.sh'}) == assets(task, {'solution/solve.sh'})
            if name == 'native_reference':
                assert assets(bundle) == actual
            details_files = list((root / 'cases/jobs' / name).rglob('reward-details.json'))
            assert len(details_files) == 1
            details = json.loads(details_files[0].read_text())
            assert details == case['native_grade_details']
            reward = details['reward']
            assert details['parse_status'] == 'ok'
            assert (details['f2p_total'], details['p2p_total']) == (item['F2P'], item['P2P'])
            assert case['completed'] and case['exception_type'] is None and case['returncode'] == 0
            assert case['reward'] == reward
            raw_grade = native_grade(details_files[0].parent.parent, f2p, p2p)
            assert raw_grade['reward'] == reward
            reward_matches = 0 < reward < 1 if expected[name] == 'fractional' else reward == expected[name]
            if expected[name] == 1:
                assert details['resolved'] and details['command_resolved'] and details['exit_code'] == 0
                assert not details['untracked_failed'] and not details['regressions']
            assert case['passed'] == reward_matches
            if not allow_failed_controls:
                assert reward_matches
            cases.append({'case': name, 'reward': reward, 'expected_reward': expected[name], 'acceptance_control_passed': reward_matches, 'raw_test_grade': raw_grade, 'parse_status': details['parse_status'], 'F2P_passed': details['f2p_passed'], 'F2P_total': item['F2P'], 'P2P_passed': details['p2p_passed'], 'P2P_total': item['P2P']})
        all_passed = all(case['acceptance_control_passed'] for case in cases)
        assert row['all_controls_passed'] == all_passed
        records.append({'pr': pr, 'repository_key': item['repository_key'], 'portable_asset_sha256': sha, 'native_instruction_grader_reference_unchanged': True, 'control_bundles_change_only_solution_script': True, 'separate_oracle_and_grading_assets': True, 'offline_runtime_and_terminal_tooling_configured': True, 'six_controls_passed': all_passed, 'cases': cases})
    limitations = ['Public durable readback and exact sandbox cleanup are separate gates.', 'Checks cover the native test contract, not exhaustive software correctness.', 'No end-to-end grader-integrity diagnostic is claimed.', 'Parent package/OS indexes and image tags remain rebuild dependencies.', 'Public historical PR lineages overlap other recipe cohorts and are not independent scientific domains.']
    prs = {row['pr'] for row in records}
    if 5308 in prs:
        limitations.append('PR5308 instruction reveals the five-field hash implementation; low-complexity software maintenance.')
    if 2636 in prs:
        limitations.extend(['PR2636 uses CPU mock modules, not physical GPU hardware; original PR-body implementation guidance and truncated performance section remain.', 'PR2636 alternative retains reference-patch scaffolding and rewrites the memory-error classifier; not a wholly independent implementation.'])
    if 5316 in prs:
        limitations.append('PR5316 is low-complexity CompoundLocation hashing with implementation guidance and shares issue5193/competency with PR5308.')
    stage = 'independent_correctness_gates_passed_public_preservation_pending' if all(row['six_controls_passed'] for row in records) else 'native_evidence_audited_acceptance_controls_failed_not_admitted'
    return {'stage': stage, 'records': records, 'controls_executed': sum(len(x['cases']) for x in records), 'model_calls': 0, 'blind_attempts': 0, 'Atlas_admissions': 0, 'limitations': limitations}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path(__file__).parent / 'pr-correctness-input-manifest.json')
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--skbio-source', type=Path, required=True)
    parser.add_argument('--biopython-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-failed-controls', action='store_true', help='Preserve audited negative findings without declaring acceptance.')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    result = audit(args.evidence_root, manifest, {'skbio': args.skbio_source, 'biopython': args.biopython_source}, allow_failed_controls=args.allow_failed_controls)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'stage': result['stage'], 'candidates': len(result['records']), 'controls': result['controls_executed']}))
