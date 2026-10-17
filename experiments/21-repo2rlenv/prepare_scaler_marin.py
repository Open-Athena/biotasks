"""Prepare full, separate-context SCALER TaskSpecs without running or grading them."""
import argparse
import base64
import hashlib
import json
import tomllib
from pathlib import Path


def resources(folder):
    result = []
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Linked input requires explicit review')
        if path.is_file():
            assert path.stat().st_size < 1024**2
            result.append({'path': str(path.relative_to(folder)),
                           'source': {'kind': 'inline_file', 'content_base64': base64.b64encode(path.read_bytes()).decode()},
                           'mode': format(path.stat().st_mode & 0o777, '04o')})
    return result


def prepare(tasks, output, control_path):
    output.mkdir(exist_ok=False, parents=True)
    controls = json.loads(control_path.read_text())
    records = []
    for task in sorted(tasks.iterdir()):
        if not task.is_dir():
            continue
        config = tomllib.loads((task / 'task.toml').read_text())
        assert config['verifier']['environment_mode'] == 'separate'
        assert config['artifacts'] == [{'source': '/workspace/answer.txt'}]
        assert config['metadata']['repo2env']['answer_contract'] == {'output_type': 'number'}
        assets = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(task.rglob('*')) if p.is_file()}
        identity = hashlib.sha256(json.dumps(assets, sort_keys=True).encode()).hexdigest()
        environment = lambda folder: {
            'capabilities': ['shell', 'filesystem'], 'command_semantics': 'linux_process',
            'working_directory': '/workspace', 'docker_build': {'files': resources(task / folder)}}
        tests = resources(task / 'tests')
        spec = {'schema_version': '0.27', 'id': 'repo2rlenv-scaler/' + identity,
                'source': {'dataset': 'Open-Athena/biotasks-issue-21', 'revision': 'sha256:' + identity,
                           'row': task.name, 'importer_revision': 'sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                'context': {'events': [{'type': 'message', 'role': 'user', 'content': (task / 'instruction.md').read_text()}]},
                'answer_type': 'workspace_state', 'answer_format': {'kind': 'plain_text'},
                'output_paths': ['/workspace/answer.txt'], 'environment_requirements': environment('environment'),
                'resources': {'worker': [], 'oracle': resources(task / 'solution'),
                              'verifier': [x for x in tests if x['path'] != 'Dockerfile']},
                'grader': {'kind': 'script', 'argv': ['sh', '/tests/test.sh'], 'cwd': '/workspace',
                           'environment': environment('tests'), 'answer_path': None,
                           'artifacts': [{'source': '/workspace/answer.txt', 'target': '/workspace/answer.txt', 'kind': 'file', 'missing': 'error'}],
                           'reward': {'kind': 'file', 'files': [{'path': '/logs/verifier/reward.txt', 'format': 'number'}]},
                           'timeout': 60},
                'tags': ['repo2rlenv', 'scaler', 'synthetic', 'native_reward_minus_one_plus_one', 'unvalidated']}
        path = output / (task.name + '.json')
        path.write_text(json.dumps(spec, indent=2) + '\n')
        rows = [x for x in controls['cases'] if x['task'] == task.name]
        assert len(rows) == 4
        assert all(x['grader_sha256'] == assets['tests/grade.py'] and x['reference_sha256'] == assets['tests/reference.json'] for x in rows)
        records.append({'task': task.name, 'task_id': spec['id'], 'file': path.name,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'asset_sha256': assets,
                        'cases': rows})
    assert len(records) == 3
    result = {'stage': 'prepared_unvalidated', 'marin_revision': '45a044387ccd95ab698b4a592056aadaff961540',
              'tasks': records, 'native_reward_range': [-1, 1], 'model_calls': 0,
              'runtime_parity_executed': False,
              'limitations': ['Marin runtime must retain negative rewards without clipping or normalization.',
                              'Inspect returned score-range metadata separately; default bounds may differ.',
                              'Offline learner network policy is enforced by execution harness.']}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for arg in ('tasks', 'output', 'controls'):
        parser.add_argument('--' + arg, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.tasks, args.output, args.controls)
