"""Validate the prepared commit mapping against the pinned Marin schema only."""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REVISION = '45a044387ccd95ab698b4a592056aadaff961540'


def check(output):
    from shellbox.machine import UnsupportedMachineSpec
    from taskcompendium.models import TaskSpec, require_resolved_environment

    raw = Path('task.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == os.environ['BIOTASKS21_TASK_SPEC_SHA256']
    original = json.loads(raw)
    spec = TaskSpec.model_validate_json(raw)
    assert spec.id == 'repo2rlenv-commit-runtime/a26ec72cc2e4b5ce6b9383ba0803b746a556254abb1be45bf7dd97c66313481f'
    assert original['source']['row'] == 'scikit-bio/scikit-bio@d25f305cea3a6cc200b0fe10806151132b395bcf'
    assert not spec.resources.worker and not spec.resources.all
    assert spec.resources.oracle and spec.resources.verifier
    try:
        require_resolved_environment(spec.environment_requirements)
    except UnsupportedMachineSpec:
        rejected = True
    else:
        raise AssertionError('Unresolved source build cannot execute before image resolution')
    record = {'stage': 'pinned_Marin_commit_TaskSpec_schema_validated_only',
              'task_id': spec.id, 'source_row': original['source']['row'],
              'task_spec_sha256': hashlib.sha256(raw).hexdigest(), 'marin_revision': REVISION,
              'worker_resources': len(spec.resources.worker), 'oracle_resources': len(spec.resources.oracle),
              'verifier_resources': len(spec.resources.verifier), 'unresolved_execution_rejected': rejected,
              'model_calls': 0, 'sandbox_allocations': 0, 'target_repository_execution': False,
              'paired_native_Marin_controls_executed': False, 'Atlas_admitted': False}
    (output / 'schema-result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    return 0


def main():
    output = Path(os.environ['IRIS_OUTPUT_DIR']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert not os.environ.get('DAYTONA_API_KEY') and not os.environ.get('BIOTASKS21_GLM_KEY')
    if os.environ.get('BIOTASKS21_SCHEMA_CHILD') == '1':
        return check(output)
    state = {'stage': 'pinned_Marin_schema_setup', 'status': 'started', 'model_calls': 0,
             'sandbox_allocations': 0, 'target_repository_execution': False}
    started = time.monotonic()
    try:
        root = Path('schema-runtime')
        root.mkdir(exist_ok=False)
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV', None)
        env['UV_PROJECT_ENVIRONMENT'] = str(root.resolve() / '.venv')
        with (output / 'private-setup.log').open('w') as log:
            for command in [
                ['git', 'init', str(root)],
                ['git', '-C', str(root), 'remote', 'add', 'origin', 'https://github.com/marin-community/marin.git'],
                ['git', '-C', str(root), 'fetch', '--depth=1', 'origin', REVISION],
                ['git', '-C', str(root), 'checkout', '--detach', 'FETCH_HEAD'],
                ['uv', 'sync', '--frozen', '--no-dev', '--package', 'marin-taskcompendium',
                 '--python', '3.12.3', '--project', str(root)],
            ]:
                subprocess.run(command, env=env, stdout=log, stderr=log, check=True, timeout=600)
            actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
            assert actual == REVISION
            env['BIOTASKS21_SCHEMA_CHILD'] = '1'
            result = subprocess.run([str(root.absolute() / '.venv/bin/python'), str(Path(__file__).absolute())],
                                    env=env, stdout=log, stderr=log, timeout=120)
        with (root / 'uv.lock').open('rb') as stream:
            state['marin_uv_lock_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        state.update(status='schema_passed' if result.returncode == 0 else 'schema_failed',
                     child_exit_code=result.returncode, marin_revision=actual)
        return result.returncode
    except Exception as exc:
        state.update(status='setup_or_schema_failed', error_type=type(exc).__name__)
        return 1
    finally:
        state['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    sys.exit(main())
