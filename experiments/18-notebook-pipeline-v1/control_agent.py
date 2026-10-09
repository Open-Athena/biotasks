"""Submit a preserved control artifact through Harbor; never call a model."""

import shlex
from pathlib import Path, PurePosixPath

from harbor.agents.base import BaseAgent


class ArtifactControlAgent(BaseAgent):
    def __init__(self, *args, artifact_path=None, destination=None, artifacts=None, **kwargs):
        super().__init__(*args, **kwargs)
        if artifacts is not None and artifact_path is not None:
            raise ValueError("Use either the current artifact list or historical single artifact")
        self.artifacts = (
            artifacts
            if artifacts is not None
            else ([{"source": artifact_path, "destination": destination}] if artifact_path else [])
        )

    @staticmethod
    def name():
        return "artifact-control"

    def version(self):
        return "2"

    async def setup(self, environment):
        for artifact in self.artifacts:
            if not Path(artifact["source"]).is_file():
                raise ValueError("Recorded control artifact is missing")
            if not PurePosixPath(artifact["destination"]).is_absolute():
                raise ValueError("Control output requires an absolute path")

    async def run(self, instruction, environment, context):
        for artifact in self.artifacts:
            parent = str(PurePosixPath(artifact["destination"]).parent)
            result = await environment.exec(
                command="mkdir -p " + shlex.quote(parent), timeout_sec=10
            )
            if result.return_code:
                raise RuntimeError("Could not prepare control output directory")
            await environment.upload_file(Path(artifact["source"]), artifact["destination"])
        context.n_input_tokens = 0
        context.n_output_tokens = 0
        context.cost_usd = 0
        context.metadata = {
            "stage": "control_submission",
            "model_called": False,
            "empty": not self.artifacts,
            "artifact_count": len(self.artifacts),
        }
