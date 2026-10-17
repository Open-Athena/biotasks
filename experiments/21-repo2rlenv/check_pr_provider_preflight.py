"""Offline checks of provider configuration, fail-closed readiness, and cleanup."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pr_provider_environment as provider
import run_pr_provider_preflight as runner

ROOT = Path(__file__).resolve().parent

async def check():
    task=ROOT/'evidence/marin-pr2633-preparation/harbor-task'
    runner.check_task(task,ROOT/'evidence/pr2633-acceptance/acceptance.json')
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp)
        for agent in ('nop','oracle'):
            spec=runner.config(task,out,agent)
            assert spec.agent.name==agent and spec.agent.model_name is None
            assert spec.environment.override_cpus==2
            assert spec.environment.override_memory_mb==4096
            assert spec.environment.override_storage_mb==10240
            assert spec.environment.override_gpus==0 and spec.environment.delete
        observed=[]
        async def get(identity):return SimpleNamespace(id=identity,network_block_all=True)
        client=SimpleNamespace(get=get)
        env=object.__new__(provider.RecordedDaytonaEnvironment)
        env._sandbox=SimpleNamespace(id='synthetic-sandbox')
        env._client_manager=SimpleNamespace(get_client=AsyncMock(return_value=client))
        with patch.object(provider.DaytonaEnvironment,'start',new=AsyncMock()),patch.object(provider.RecordedDaytonaEnvironment,'exec',new=AsyncMock(return_value=SimpleNamespace(return_code=0))),patch.object(provider,'record',new=observed.append):
            await env.start(False)
        assert observed[-1]['network_block_all'] and observed[-1]['private_paths_and_import_returncode']==0
        async def blocked_get(identity):return SimpleNamespace(id=identity,network_block_all=False)
        client.get=blocked_get
        with patch.object(provider.DaytonaEnvironment,'start',new=AsyncMock()):
            try:await env.start(False)
            except AssertionError:pass
            else:raise AssertionError('Unblocked network accepted')
        client.get=get
        with patch.object(provider.DaytonaEnvironment,'start',new=AsyncMock()),patch.object(provider.RecordedDaytonaEnvironment,'exec',new=AsyncMock(return_value=SimpleNamespace(return_code=1))),patch.object(provider,'record',new=observed.append):
            try:await env.start(False)
            except AssertionError:pass
            else:raise AssertionError('Failed learner check accepted')
        (out/'provider.jsonl').write_text(json.dumps({'sandbox_id':'synthetic-sandbox'})+'\n')
        actions=[]
        class Client:
            deleted=False
            def get(self,identity):
                assert identity=='synthetic-sandbox'
                if self.deleted:raise runner.DaytonaNotFoundError('fixture absent')
                return SimpleNamespace(id=identity)
            def delete(self,sandbox,timeout):
                actions.append(sandbox.id);self.deleted=True
        with patch.object(runner,'Daytona',new=Client):runner.cleanup(out)
        assert actions==['synthetic-sandbox']
        assert json.loads((out/'cleanup.json').read_text())[0]['confirmed_absent']
    print('PASS: real Harbor config, asset identity, network/readiness rejection and owned-sandbox cleanup; zero provider/model calls')

asyncio.run(check())
