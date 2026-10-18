"""Execute native graded correctness controls remotely, with no model calls."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tarfile
from pathlib import Path

from prepare_pr_correctness_controls import assets, controls, portable
from repo2rlenv.execution.harbor import read_trial
from repo2rlenv.execution.lifecycle import save_record


def result_passed(row, details, expected_totals):
    parsed = details.get('parse_status') == 'ok' and (details.get('f2p_total'), details.get('p2p_total')) == expected_totals
    expected, reward = row['expected_reward'], row.get('reward')
    reward_ok = reward is not None and (0 < reward < 1 if expected == 'fractional' else reward == expected)
    full_ok = expected != 1 or details.get('resolved') is True and details.get('command_resolved') is True
    return row.get('returncode') == 0 and row.get('completed') is True and row.get('exception_type') is None and parsed and reward_ok and full_ok


def run_case(case, *, output, expected_totals):
    name = case['case']
    job = output / 'jobs' / name
    command = [str(Path(sys.executable).with_name('harbor')), 'run', '--path', case['bundle'], '--agent', 'oracle', '--env', 'repo2rlenv.execution.harbor_offline:OfflineDockerEnvironment', '--n-concurrent', '1', '--max-retries', '0', '--job-name', name, '--jobs-dir', str(output / 'jobs'), '--quiet']
    row = {'case': name, 'expected_reward': case['expected_reward'], 'stage': 'running', 'timeout_sec': 900, 'command': command}
    try:
        with (output / (name + '.log')).open('w') as log:
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
        evidence = read_trial(job)
        details_files = list(job.rglob('reward-details.json'))
        if len(details_files) != 1:
            raise ValueError('Expected one native graded detail file')
        details = json.loads(details_files[0].read_text())
        row.update(stage='completed', completed=evidence.completed, reward=evidence.reward, exception_type=evidence.exception_type, native_grade_details=details, grade_details_path=str(details_files[0]))
        row['passed'] = result_passed(row, details, expected_totals)
    except Exception as exc:
        row.update(stage='control_failed', error_type=type(exc).__name__, passed=False)
    return row


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Target execution requires the authorized remote worker')
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / 'manifest.json').read_text())
    if not 1 <= len(manifest['tasks']) <= 3 or not {item['pr'] for item in manifest['tasks']} <= {2630, 5317, 5308, 5316, 2636} or len({item['pr'] for item in manifest['tasks']}) != len(manifest['tasks']) or manifest['model_calls'] != 0:
        raise ValueError('Unexpected frozen control cohort')
    args.output.mkdir(parents=True, exist_ok=False)
    extracted = Path('/work/native/control-sources')
    extracted.mkdir(exist_ok=False)
    for item in manifest['archives']:
        file = args.inputs / item['filename']
        with file.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']
        destination = extracted / item['repository_key']
        destination.mkdir()
        with tarfile.open(file) as archive:
            assert all(m.isfile() or m.isdir() for m in archive.getmembers())
            archive.extractall(destination, filter='data')
    rows = []
    for item in manifest['tasks']:
        pr = item['pr']
        task_record = {'pr': pr, 'stage': 'preparing', 'cases': [], 'model_calls': 0, 'independently_admitted': False}
        rows.append(task_record)
        output = args.output / f'pr{pr}'
        output.mkdir()
        try:
            root = extracted / item['repository_key']
            native = root / item['task_member']
            baseline = root / item['baseline_member']
            prepared, profile = portable(native, baseline, output / 'portable', pr=pr)
            profile_hash = hashlib.sha256(json.dumps(profile['portable_assets'], sort_keys=True).encode()).hexdigest()
            if profile_hash != item['portable_asset_manifest_sha256']:
                raise ValueError('Prepared runtime assets differ from the checkpointed preview')
            cases = controls(prepared, output / 'controls', pr=pr)
            (output / 'cases').mkdir()
            for case in cases['cases']:
                assert assets(Path(case['bundle']), exclude={'solution/solve.sh'}) == cases['unchanged_assets']
                row = run_case(case, output=output / 'cases', expected_totals=(item['F2P'], item['P2P']))
                task_record['cases'].append(row)
                save_record(args.output / 'summary.json', {'stage': 'independent_native_graded_controls_not_admission', 'records': rows})
            task_record.update(stage='completed', all_controls_passed=all(row['passed'] for row in task_record['cases']), profile_asset_sha256=profile_hash)
        except Exception as exc:
            task_record.update(stage='task_controls_failed', error_type=type(exc).__name__, all_controls_passed=False)
        save_record(args.output / 'summary.json', {'stage': 'independent_native_graded_controls_not_admission', 'records': rows})
    print('BIOTASKS21_PR_CORRECTNESS_SUMMARY ' + json.dumps({'records': [{k: value for k, value in row.items() if k != 'cases'} | {'cases': [{k: case[k] for k in ('case', 'stage', 'reward', 'passed', 'error_type') if k in case} for case in row['cases']]} for row in rows], 'model_calls': 0}), flush=True)
    if not all(row.get('all_controls_passed') for row in rows):
        raise RuntimeError('Some independent native controls did not pass')


if __name__ == '__main__':
    main()
