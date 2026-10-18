"""Export one saved native Smith contrast and measure source-level controls.

Runs only on an authorized remote build/test worker. No model calls, new
candidates, grader modifications or solver attempts occur here.
"""
import argparse
import ast
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import tomli_w

from prepare_pr_correctness_controls import assets
from repo2rlenv.execution.harbor import read_trial
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_smith.export import export_candidate
from repo2rlenv.pipelines.recipes.swe_smith.options import SWESmithOptions

IDENTIFIER = '539b25a8eba699d3de89'
SOURCE = 'skbio/diversity/alpha/_base.py'


def replace_body(source, body):
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'robbins']
    if len(nodes) != 1:
        raise ValueError('Expected one Robbins function')
    node = nodes[0]
    statements = node.body
    if isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements = statements[1:]
    lines = source.splitlines(keepends=True)
    indent = ' ' * statements[0].col_offset
    lines[statements[0].lineno - 1:node.end_lineno] = [indent + line + '\n' for line in body.splitlines()]
    changed = ''.join(lines)
    ast.parse(changed)
    return changed


def prepare_cases(task, output):
    original = assets(task)
    configuration = tomllib.loads((task / 'task.toml').read_text())
    profile = output / 'offline-task'
    shutil.copytree(task, profile)
    for phase in ('environment', 'agent', 'verifier'):
        configuration.setdefault(phase, {})['network_mode'] = 'no-network'
    configuration['environment'].update(cpus=1, memory_mb=2048)
    metadata = configuration['metadata']['repo2env']
    metadata['original_content_hash'] = metadata.pop('content_hash', '')
    metadata['validation_profile'] = 'explicit_offline_Smith_source_controls_not_admission'
    (profile / 'task.toml').write_text(tomli_w.dumps(configuration))
    compose = profile / 'environment/docker-compose.yaml'
    if compose.is_file():
        compose.unlink()
    excluded = {'task.toml', 'environment/docker-compose.yaml'}
    assert assets(task, exclude=excluded) == assets(profile, exclude=excluded)
    fixed = assets(profile, exclude={'solution/solve.sh'})
    source = (profile / 'environment/source' / SOURCE).read_text()
    alternatives = {
        'alternative': 'singletons = sum(1 for value in counts if value == 1)\nreturn np.float64(singletons / sum(counts))',
        'alternative_repeat': 'singletons = sum(1 for value in counts if value == 1)\nreturn np.float64(singletons / sum(counts))',
        'incorrect_zero': 'return np.float64(0.0)',
        'incorrect_constant_example': 'return np.float64(2 / 7)',
    }
    rows = []
    for name, expected in [('baseline', 0), ('native_reference', 1), ('alternative', 1), ('alternative_repeat', 1), ('incorrect_zero', 0), ('incorrect_constant_example', 0)]:
        destination = output / 'cases' / name
        shutil.copytree(profile, destination)
        if name == 'baseline':
            script = '#!/bin/sh\nset -eu\n# Preserve the original defective library source.\n'
        elif name in alternatives:
            changed = replace_body(source, alternatives[name])
            program = "from pathlib import Path\nPath('/workspace/" + SOURCE + "').write_text(" + repr(changed) + ")\n"
            script = "#!/bin/sh\nset -eu\npython3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n'
        else:
            script = (profile / 'solution/solve.sh').read_text()
        path = destination / 'solution/solve.sh'
        path.write_text(script)
        path.chmod(0o755)
        assert assets(destination, exclude={'solution/solve.sh'}) == fixed
        rows.append({'case': name, 'bundle': str(destination), 'expected_reward': expected})
    result = {'stage': 'prepared_not_executed', 'candidate_id': IDENTIFIER, 'native_task_relative_path': task.relative_to(output).as_posix(), 'native_assets': original, 'profile_assets': assets(profile), 'changed_profile_assets': sorted(excluded), 'case_unchanged_assets': fixed, 'cases': rows, 'model_calls': 0, 'reward_contract': 'binary all native expected tests pass; no fractional score'}
    save_record(output / 'control-manifest.json', result)
    return rows, fixed


def run_case(case, output, expected_tests):
    command = [str(Path(sys.executable).with_name('harbor')), 'run', '--path', case['bundle'], '--agent', 'oracle', '--env', 'repo2rlenv.execution.harbor_offline:OfflineDockerEnvironment', '--n-concurrent', '1', '--max-retries', '0', '--job-name', case['case'], '--jobs-dir', str(output / 'jobs'), '--quiet']
    row = {**case, 'command': command, 'stage': 'running', 'timeout_sec': 900}
    try:
        with (output / (case['case'] + '.log')).open('w') as log:
            child = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
            try:
                row['returncode'] = child.wait(timeout=900)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
        job = output / 'jobs' / case['case']
        evidence = read_trial(job)
        files = list(job.glob('**/verifier/result.json'))
        if len(files) != 1:
            raise ValueError('Expected one native verifier result')
        native = json.loads(files[0].read_text())
        statuses = native.get('statuses') or {}
        row.update(stage='completed', completed=evidence.completed, reward=evidence.reward, exception_type=evidence.exception_type, native_result=native, expected_test_names_match=set(statuses) == expected_tests)
        row['executed_and_parsed'] = row['returncode'] == 0 and evidence.completed and evidence.exception_type is None and row['expected_test_names_match']
        row['passed'] = row['executed_and_parsed'] and evidence.reward == case['expected_reward']
    except Exception as exc:
        row.update(stage='execution_failed', error_type=type(exc).__name__, passed=False, executed_and_parsed=False)
    return row


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Native target execution requires the authorized remote worker')
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / 'manifest.json').read_text())
    assert manifest['candidate_id'] == IDENTIFIER and manifest['model_calls'] == 0
    args.output.mkdir(parents=True, exist_ok=False)
    for name, record in manifest['files'].items():
        file = args.inputs / name
        with file.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256']
    unpacked = Path('/work/native/robbins-generation')
    unpacked.mkdir(exist_ok=False)
    with tarfile.open(args.inputs / 'generation-evidence.tar.gz') as archive:
        archive.extractall(unpacked, filter='data')
    generation = unpacked / 'native/generation'
    candidates = json.loads((generation / 'generation.json').read_text())['candidates']
    candidate = next(x for x in candidates if x['id'] == IDENTIFIER)
    authored = json.loads((args.inputs / 'issues.json').read_text())['records']
    issue = next(x for x in authored if x['candidate_id'] == IDENTIFIER)
    assert issue['status'] == 'authored'
    options = SWESmithOptions.model_validate(json.loads((args.inputs / 'config.json').read_text())['options'])
    task = export_candidate(generation, candidate, options, issue['issue'], args.output / 'native-task', org='open-athena')
    contract = json.loads((task / 'tests/contract.json').read_text())
    assert contract['submitted_files'] == [SOURCE]
    expected_tests = set(candidate['contrast']['FAIL_TO_PASS'] + candidate['contrast']['PASS_TO_PASS'])
    assert set(contract['expected_passes']) == expected_tests
    cases, fixed = prepare_cases(task, args.output)
    records = []
    summary = {'stage': 'independent_native_Smith_source_controls_not_admission', 'candidate_id': IDENTIFIER, 'model_calls': 0, 'native_export_completed': True, 'records': records, 'independently_admitted': False}
    for case in cases:
        assert assets(Path(case['bundle']), exclude={'solution/solve.sh'}) == fixed
        records.append(run_case(case, args.output, expected_tests))
        save_record(args.output / 'summary.json', summary)
    summary.update(all_controls_passed=all(x['passed'] for x in records), all_controls_executed_and_parsed=all(x['executed_and_parsed'] for x in records))
    save_record(args.output / 'summary.json', summary)
    print('BIOTASKS21_ROBBINS_NATIVE_CONTROLS ' + json.dumps({'candidate_id': IDENTIFIER, 'all_controls_passed': summary['all_controls_passed'], 'records': [{k: row.get(k) for k in ('case', 'stage', 'reward', 'passed', 'executed_and_parsed', 'error_type')} for row in records]}), flush=True)
    if not summary['all_controls_executed_and_parsed']:
        raise RuntimeError('Some native source controls did not execute and parse')


if __name__ == '__main__':
    main()
