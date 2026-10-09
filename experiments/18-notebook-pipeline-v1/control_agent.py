"""Submit a preserved control artifact through Harbor; never call a model."""

import shlex
from pathlib import Path, PurePosixPath

from harbor.agents.base import BaseAgent


class ArtifactControlAgent(BaseAgent):
    def __init__(self, *args, artifact_path=None, destination=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_path = Path(artifact_path) if artifact_path else None
        self.destination = destination

    @staticmethod
    def name():
        return "artifact-control"

    def version(self):
        return "1"

    async def setup(self, environment):
        if self.artifact_path is not None and not self.artifact_path.is_file():
            raise ValueError("Recorded control artifact is missing")

    async def run(self, instruction, environment, context):
        if self.artifact_path is not None:
            parent = str(PurePosixPath(self.destination).parent)
            result = await environment.exec(
                command="mkdir -p " + shlex.quote(parent), timeout_sec=10
            )
            if result.return_code:
                raise RuntimeError("Could not prepare control output directory")
            await environment.upload_file(self.artifact_path, self.destination)
        context.n_input_tokens = 0
        context.n_output_tokens = 0
        context.cost_usd = 0
        context.metadata = {
            "stage": "control_submission",
            "model_called": False,
            "empty": self.artifact_path is None,
        }
