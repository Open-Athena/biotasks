"""Remote no-model provider check for one independently accepted SCALER task."""
import json
import os
import subprocess
import time
import traceback
from pathlib import Path

from check_pr_provider_setup import main as prepare


def main():
    started = time.monotonic()
    capture = Path(os.environ['IRIS_OUTPUT_DIR'])
    capture.mkdir(parents=True, exist_ok=True)
    try:
        os.environ['BIOTASKS21_PROVIDER_MODULE'] = 'scaler_provider_environment'
        root, env = prepare()
        remaining = int(1800 - (time.monotonic() - started))
        if remaining < 60:
            raise TimeoutError('Compatibility setup exhausted deadline')
        env.update(REPO2RLENV_MODEL_WORKER='1',
                   BIOTASKS21_PREFLIGHT_REMAINING_SEC=str(remaining))
        with (capture / 'provider-controller.log').open('w') as log:
            result = subprocess.run(
                [str(root / '.venv/bin/python'), 'run_pr_provider_preflight.py',
                 '--task', 'task', '--acceptance', 'acceptance.json',
                 '--output', 'provider-output'], env=env, stdout=log, stderr=log,
                timeout=remaining + 240)
        (capture / 'wrapper-status.json').write_text(json.dumps({
            'stage': 'no_model_provider_preflight',
            'child_exit_code': result.returncode}))
        return result.returncode
    except Exception as exc:
        (capture / 'wrapper-status.json').write_text(json.dumps({
            'stage': 'setup_or_controller', 'error_type': type(exc).__name__,
            'error': str(exc)}))
        (capture / 'wrapper-traceback.txt').write_text(traceback.format_exc())
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
