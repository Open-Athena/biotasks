"""Check single-child dispatch and missing-evidence rejection without services."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_scaler_blind_remote as runner

original = Path.cwd()
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    try:
        os.chdir(root)
        with patch.dict(os.environ, {'IRIS_OUTPUT_DIR': str(root / 'missing')}), \
             patch.object(runner, 'prepare') as prepare, \
             patch.object(runner, 'resolve_endpoint') as resolve, \
             patch.object(runner.subprocess, 'run') as spawn:
            assert runner.main() == 1
            prepare.assert_not_called()
            resolve.assert_not_called()
            spawn.assert_not_called()
        for name in ('baseline-result.json', 'reference-status.json', 'acceptance.json'):
            Path(name).write_text('{}')
        for code in (0, 1):
            target = root / str(code)
            with patch.dict(os.environ, {'IRIS_OUTPUT_DIR': str(target)}), \
                 patch.object(runner, 'prepare', return_value=(root, {})), \
                 patch.object(runner, 'resolve_endpoint', return_value='https://fixture.invalid/v1'), \
                 patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(returncode=code)) as spawn:
                assert runner.main() == code
                spawn.assert_called_once()
                args, kwargs = spawn.call_args
                assert args[0][1] == 'run_pr_blind_solver.py'
                assert kwargs['timeout'] == 1200
                assert kwargs['env']['BIOTASKS21_PROVIDER_MODULE'] == 'scaler_provider_environment'
                state = json.loads((target / 'wrapper-status.json').read_text())
                assert state['child_exit_code'] == code and state['attempt_limit'] == 1
    finally:
        os.chdir(original)
print('PASS: missing controls reject before setup; single solver child; return status propagated; no services called.')
