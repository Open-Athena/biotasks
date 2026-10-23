"""A frozen staging recipe must see the same controller-owned input roots."""

import asyncio
import shlex
import subprocess

import pytest
from grading_session import GradingSession


def test_materialization_staging_has_the_setup_input_roots(tmp_path):
    fixture = tmp_path / "original.txt"
    fixture.write_text("unchanged source input\n")
    source = tmp_path / "reference"
    (source / "candidate").mkdir(parents=True)
    (source / "trial").mkdir()
    (source / "candidate/pyproject.toml").write_text("fixture environment")
    (source / "trial/uv.lock").write_text("fixture lock")
    # No mkdir in this valid recipe: setup/replay provision both allowed roots.
    (source / "candidate/stage-inputs.sh").write_text(
        f"cp {shlex.quote(str(fixture))} /inputs/source.txt\n"
        f"cp {shlex.quote(str(fixture))} /work/cache/source.txt\n"
    )
    workspace = tmp_path / "sandbox"
    events = []

    class EnvironmentBuilt(Exception):
        pass

    class LocalWorkspace:
        def local(self, path):
            return workspace / path.removeprefix("/")

        async def upload(self, local, remote):
            target = self.local(remote)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(local.read_bytes())

        async def command(self, argv, seconds, label):
            events.append(label)
            if label == "grading-initialize":
                assert argv[:2] == ["mkdir", "-p"]
                for path in argv[2:]:
                    self.local(path).mkdir(parents=True, exist_ok=True)
            if label == "grading-environment":
                script = self.local("/work/stage-inputs.sh").read_text()
                for path in ["/work/cache", "/inputs"]:
                    script = script.replace(path, shlex.quote(str(self.local(path))))
                result = subprocess.run(["sh", "-eu", "-c", script], capture_output=True, text=True)
                return {"exit_code": result.returncode, "log": result.stderr}
            return {"exit_code": 0, "log": ""}

        async def network(self, blocked):
            assert blocked is False  # Setup only; no model or network request.

        async def download(self, *args):
            # Stop after the actual staging commands succeed; later numerical
            # comparison and user isolation have separate executable coverage.
            raise EnvironmentBuilt

    remote = LocalWorkspace()
    session = GradingSession(
        remote=remote,
        snapshot={"directory": source, "system_packages": [], "outputs": []},
        root=tmp_path / "session",
        config={"materialize_task": True, "setup_seconds": 60},
    )

    async def initialize_users(*args):
        pass

    session.helper = initialize_users
    with pytest.raises(EnvironmentBuilt):
        asyncio.run(session.initialize())
    assert events.index("grading-initialize") < events.index("grading-environment")
    for path in ["/inputs/source.txt", "/work/cache/source.txt"]:
        assert remote.local(path).read_bytes() == fixture.read_bytes()
    assert fixture.read_text() == "unchanged source input\n"
