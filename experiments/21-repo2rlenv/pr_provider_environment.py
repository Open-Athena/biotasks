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
    def readiness_command(self):
        return ("test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch && "
                "cd /workspace && python -c 'import skbio,numpy,scipy,pandas; "
                "from skbio.stats.composition import ancombc2'")

    def check_terminal(self):
        return bool(os.environ.get('BIOTASKS21_RUNTIME_MANIFEST'))

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
            command=self.readiness_command(),
            timeout_sec=60,
        )
        record({'stage': 'learner_preflight', 'sandbox_id': sandbox.id,
                'network_block_all': sandbox.network_block_all,
                'private_paths_and_import_returncode': result.return_code})
        assert result.return_code == 0, 'Learner readiness or private path check failed'

        if self.check_terminal():
            from harbor.agents.terminus_2.tmux_session import TmuxSession
            installed = await self.exec(command='tmux -V', timeout_sec=15)
            assert installed.return_code == 0, 'tmux must be preinstalled for offline solver'
            session = TmuxSession(
                session_name='biotasks21-setup-check', environment=self,
                logging_path=Path('/tmp/biotasks21-terminal-check.log'),
                local_asciinema_recording_path=None, remote_asciinema_recording_path=None,
                user=self.default_user,
            )
            try:
                await session.start()
                live = await self.exec(command='tmux has-session -t biotasks21-setup-check', timeout_sec=15)
                assert live.return_code == 0
                record({'stage': 'native_terminal_setup', 'sandbox_id': sandbox.id,
                        'tmux_version': installed.stdout.strip(), 'session_started': True,
                        'model_calls': 0})
            finally:
                stopped = await self.exec(command='tmux kill-session -t biotasks21-setup-check && rm -f /tmp/biotasks21-terminal-check.log', timeout_sec=15)
                assert stopped.return_code == 0
