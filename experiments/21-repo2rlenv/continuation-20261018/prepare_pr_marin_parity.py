"""Map admitted portable PR profiles to the pinned Marin TaskSpec schema.

Preparation preserves bytes and modes; it is not schema/runtime admission.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from audit_pr_correctness_evidence import assets

MARIN_REVISION = '45a044387ccd95ab698b4a592056aadaff961540'


def resource(path, relative):
    return {'path': str(relative), 'source': {'kind': 'inline_file', 'content_base64': base64.b64encode(path.read_bytes()).decode()}, 'mode': format(path.stat().st_mode & 0o777, '04o')}


def prepare(evidence, destination, *, selected_prs=None):
    destination.mkdir(exist_ok=False)
    summary = json.loads((evidence / 'summary.json').read_text())
    records = []
    for row in summary['records']:
        pr = row['pr']
        if selected_prs is not None and pr not in selected_prs:
            continue
        assert row['all_controls_passed'] and len(row['cases']) == 6
        root = evidence / f'pr{pr}'
        task = root / 'portable/task'
        manifest = assets(task)
        identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        assert identity == row['profile_asset_sha256']
        repository = 'scikit-bio/scikit-bio' if pr in (2630, 2636) else 'biopython/biopython'
        environment = {'capabilities': ['shell', 'filesystem'], 'command_semantics': 'linux_process', 'working_directory': '/workspace', 'docker_build': {'files': [resource(task / 'environment/Dockerfile', 'Dockerfile')]}}
        spec = {'schema_version': '0.27', 'id': 'repo2rlenv-pr-runtime/' + identity,
                'source': {'dataset': 'Open-Athena/biotasks-issue-21', 'revision': 'sha256:' + identity, 'row': repository + '#' + str(pr), 'importer_revision': 'sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                'context': {'events': [{'type': 'message', 'role': 'user', 'content': (task / 'instruction.md').read_text()}]},
                'environment_requirements': environment, 'answer_type': 'workspace_state', 'answer_format': {'kind': 'plain_text'}, 'output_paths': ['/workspace'],
                'resources': {'worker': [], 'oracle': [resource(p, p.relative_to(task / 'solution')) for p in sorted((task / 'solution').rglob('*')) if p.is_file()], 'verifier': [resource(p, p.relative_to(task / 'tests')) for p in sorted((task / 'tests').rglob('*')) if p.is_file()]},
                'grader': {'kind': 'script', 'argv': ['bash', '/tests/test.sh'], 'cwd': '/workspace', 'environment': environment, 'answer_path': None, 'artifacts': [{'source': '/workspace', 'target': '/workspace', 'kind': 'directory', 'missing': 'error'}], 'reward': {'kind': 'file', 'files': [{'path': '/logs/verifier/reward.txt', 'format': 'number'}]}, 'timeout': 300.0},
                'tags': ['biology-software', 'repo2rlenv', 'pr_runtime', 'graded-correctness', 'conversion-unvalidated']}
        output = destination / f'pr{pr}'
        output.mkdir()
        (output / 'task.json').write_text(json.dumps(spec, indent=2) + '\n')
        cases = []
        for case in row['cases']:
            name = case['case']
            solution = root / 'controls' / name / 'solution/solve.sh'
            assert assets(root / 'controls' / name, {'solution/solve.sh'}) == assets(task, {'solution/solve.sh'})
            cases.append({'case': name, 'solution_shell': solution.read_text(), 'solution_mode': format(solution.stat().st_mode & 0o777, '04o'), 'requires_reference_patch': name == 'native_reference' or 'git -C /workspace apply' in solution.read_text(), 'expected_reward': case['reward'], 'native_details': case['native_grade_details'], 'solution_sha256': hashlib.sha256(solution.read_bytes()).hexdigest()})
        (output / 'controls.json').write_text(json.dumps({'pr': pr, 'cases': cases}, indent=2) + '\n')
        records.append({'pr': pr, 'repository': repository, 'task_spec': f'pr{pr}/task.json', 'control_inputs': f'pr{pr}/controls.json', 'portable_asset_sha256': identity, 'F2P': cases[0]['native_details']['f2p_total'], 'P2P': cases[0]['native_details']['p2p_total'], 'cases': len(cases), 'instruction_reference_grader_bytes_and_modes_preserved': True})
    result = {'stage': 'prepared_mapping_not_schema_or_runtime_validated', 'marin_revision': MARIN_REVISION, 'records': records, 'expected_pairs': sum(row['cases'] for row in records), 'native_plus_Marin_executions': 2 * sum(row['cases'] for row in records), 'model_calls': 0, 'blind_attempts': 0, 'Atlas_admissions': 0, 'reward_semantics': 'native graded F2P rate times P2P rate, range [0,1]', 'limitations': ['Marin schema and execution gates are not yet run.', 'Historical native profiles remain separately preserved.', 'Build tags and package/OS indexes remain external rebuild dependencies.']}
    result['files'] = {file.relative_to(destination).as_posix(): {'bytes': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted(destination.rglob('*')) if file.is_file()}
    (destination / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.evidence_root, args.output)
    print(json.dumps({'prepared_tasks': len(result['records']), 'expected_pairs': result['expected_pairs'], 'runtime_executed': False}))
