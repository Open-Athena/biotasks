"""Record owned provider sandboxes and verify learner readiness before agent setup."""
import json
import os
from pathlib import Path

from harbor.environments.daytona.environment import DaytonaEnvironment


def record(value):
    path = Path(os.environ['BIOTASKS21_PROVIDER_RECEIPTS'])
    with path.open('a') as stream:
        stream.write(json.dumps(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


class RecordedDaytonaEnvironment(DaytonaEnvironment):
    async def _create_sandbox(self, params, daytona=None):
        record({'stage': 'create_requested', 'environment_name': self.environment_name})
        try:
            return await super()._create_sandbox(params, daytona)
        finally:
            if self._sandbox is not None:
                record({'stage': 'created', 'sandbox_id': self._sandbox.id,
                        'environment_name': self.environment_name})

    async def start(self, force_build):
        await super().start(force_build)
        client = await self._client_manager.get_client()
        sandbox = await client.get(self._sandbox.id)
        assert sandbox.network_block_all is True, 'Provider must report blocked network'
        result = await self.exec(
            command="test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch && "
                    "cd /workspace && python -c 'import skbio,numpy,scipy,pandas; "
                    "from skbio.stats.composition import ancombc2'",
            timeout_sec=60,
        )
        record({'stage': 'learner_preflight', 'sandbox_id': sandbox.id,
                'network_block_all': sandbox.network_block_all,
                'private_paths_and_import_returncode': result.return_code})
        assert result.return_code == 0, 'Learner readiness or private path check failed'
