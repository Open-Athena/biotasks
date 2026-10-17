"""Ensure history probes keep no-model config and reject inputs before allocation."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import run_pr_provider_preflight as runner
import history_provider_environment as provider

async def check():
    with patch.dict(os.environ,{'REPO2RLENV_MODEL_WORKER':'1','BIOTASKS21_PROVIDER_MODULE':'history_provider_environment'}):
        spec=runner.config(Path('task'),Path('output'),'nop')
        assert spec.agent.model_name is None
        assert spec.environment.import_path=='history_provider_environment:RecordedDaytonaEnvironment'
        assert spec.environment.override_gpus==0
        args=SimpleNamespace(task=Path('task'),acceptance=Path('review'),output=Path('unused'))
        def reject(*unused):raise ValueError('fixture changed')
        with patch.object(runner,'version',return_value='0.22.0'),patch.object(runner.Trial,'create',new=AsyncMock()) as create:
            try:await runner.run(args,validate_task=reject)
            except ValueError:pass
            else:raise AssertionError('Invalid probe allocated')
            create.assert_not_called()
    for name in ('environment','tests'):
        env=object.__new__(provider.RecordedDaytonaEnvironment)
        env.environment_dir=Path(name)
        assert env.check_terminal()==(name=='environment')
        command=env.readiness_command()
        assert ('test ! -e /tests' in command)==(name=='environment')
        assert ('test -f /tests/contract.json' in command)==(name=='tests')
    assert runner.run.__kwdefaults__['validate_task'] is runner.check_task
    print('PASS: no-model history config, validation before allocation, distinct contexts, original acceptance gate retained')

asyncio.run(check())
