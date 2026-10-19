"""Sequential controls and one blind attempt per frozen admitted history task."""

import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    dispatch = Path.cwd()
    started = float(os.environ.get('BIOTASKS21_BATCH_STARTED_MONOTONIC', time.monotonic()))
    state = {'stage': 'sequential_admitted_history_task_trials', 'status': 'setup', 'units': []}
    try:
        canonical_restore = os.environ.get('BIOTASKS21_CANONICAL_RESTORE') == 'verified'
        archives = [('repo2rlenv-source.tar.gz', '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755')]
        if not canonical_restore:
            archives.append(('cohort-inputs.tar.gz', os.environ['BIOTASKS21_TASK_ARCHIVE_SHA256']))
        for filename, expected in archives:
            with Path(filename).open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        with tarfile.open('repo2rlenv-source.tar.gz') as archive:
            archive.extractall('native-runtime', filter='data')
        if not canonical_restore:
            with tarfile.open('cohort-inputs.tar.gz') as archive:
                archive.extractall('cohort', filter='data')
        cohort = json.loads(Path('cohort/manifest.json').read_text())
        minimum_client_window = cohort.get('minimum_inference_lifetime_before_unit_seconds', 3600)
        assert minimum_client_window in (930, 3600)
        assert 1 <= len(cohort['units']) <= 5
        assert len({u['task_id'] for u in cohort['units']}) == len(cohort['units'])
        root, = Path('native-runtime').iterdir()
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP='True')
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        env['PYTHONPATH'] = str(dispatch)
        with (output / 'private-setup.log').open('w') as log:
            subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'harbor', '--extra', 'daytona',
                            '--python', '3.12.3', '--project', str(root)], env=env,
                           stdout=log, stderr=log, check=True, timeout=600)
        # Keep the venv executable path: resolving its symlink would select
        # the base interpreter and lose the locked environment's site-packages.
        python = str(root.absolute() / '.venv/bin/python')
        state['status'] = 'running'
        for item in cohort['units']:
            row = {'task_id': item['task_id'], 'unit': item['unit'], 'status': 'not_started'}
            state['units'].append(row)
            # Keep the original two-hour run deadline. A task not started for
            # lack of time remains pending, without creating a blind attempt.
            remaining = 6900 - (time.monotonic() - started)
            if remaining < 3600 or float(env['BIOTASKS21_INFERENCE_EXPIRES_EPOCH']) - time.time() < minimum_client_window:
                row['status'] = 'not_started_insufficient_remaining_window'
                print('BIOTASKS21_BATCH_UNIT ' + json.dumps({'evidence': 'controller_report_only', **row}), flush=True)
                continue
            unit_output = output / item['unit']
            unit_output.mkdir(exist_ok=False)
            child_env = dict(env, IRIS_OUTPUT_DIR=str(unit_output), REPO2RLENV_MODEL_WORKER='1')
            row['status'] = 'provider_controls_running'
            (output / 'batch-status.json').write_text(json.dumps(state, indent=2) + '\n')
            print('BIOTASKS21_BATCH_UNIT ' + json.dumps({'evidence': 'controller_report_only', **row}), flush=True)
            with (unit_output / 'private-controller.log').open('w') as log:
                result = subprocess.run([python, str(dispatch / 'run_continuation_blind_trial.py')],
                                        cwd=dispatch / 'cohort' / item['unit'], env=child_env,
                                        stdout=log, stderr=log, timeout=min(3500, remaining))
            row.update(status='child_completed' if result.returncode == 0 else 'child_failed', child_exit_code=result.returncode)
            status = unit_output / 'native-trial/trial-status.json'
            if status.exists():
                trial = json.loads(status.read_text())
                row.update(native_stage=trial['status'], blind_attempts_started=trial['blind_attempts_started'])
                if trial.get('blind_result', {}).get('verifier_result'):
                    row['native_reward'] = trial['blind_result']['verifier_result']['rewards']['reward']
            cleanup = unit_output / 'native-trial/cleanup.json'
            if cleanup.exists():
                rows = json.loads(cleanup.read_text())
                row['owned_sandboxes_confirmed_absent'] = bool(rows) and all(x['confirmed_absent'] for x in rows)
            print('BIOTASKS21_BATCH_UNIT ' + json.dumps({'evidence': 'controller_report_only', **row}), flush=True)
            # A failed child may have an uncertain sandbox allocation. Preserve
            # it and stop rather than overlapping another unit before recovery.
            if result.returncode != 0 or not row.get('owned_sandboxes_confirmed_absent'):
                state['status'] = 'stopped_after_failed_or_uncertain_child'
                break
        else:
            state['status'] = 'batch_finished'
        return 0 if state['status'] == 'batch_finished' else 1
    except Exception as exc:
        state.update(status='setup_or_controller_failure', error_type=type(exc).__name__)
        return 1
    finally:
        state['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'batch-status.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
