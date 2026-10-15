"""Tool-enabled setup contract and controller-owned offline test sequence.

No local scientific execution. Remote I/O and lifecycle are injected by the host.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field
from reference_environment import validate_environment, write_environment
from reference_protocol import ReferencePlan, StrictModel, materialize
from repo2rlenv.execution.lifecycle import save_record


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class PreparedReference:
    context: dict
    plan: ReferencePlan
    baseline: str
    exports: str

    @classmethod
    def load(cls, directory: Path):
        context = json.loads((directory / "prepare/input.json").read_text())
        plan = ReferencePlan.model_validate_json((directory / "plan.json").read_text())
        baseline = context["baseline_script"]
        if digest(baseline.encode()) != context["conversion"]["script_sha256"]:
            raise ValueError("Preparation baseline identity mismatch")
        if context["source"]["source_sha256"] != context["conversion"]["source_sha256"]:
            raise ValueError("Preparation source identity mismatch")
        script, diff = materialize(baseline, plan)
        if (directory / "exports.py").read_text() != plan.export_code:
            raise ValueError("Preparation export identity mismatch")
        if (directory / "reference.py").read_text() != script:
            raise ValueError("Preparation assembled script mismatch")
        if (directory / "source.diff").read_text() != diff:
            raise ValueError("Preparation diff mismatch")
        return cls(context, plan, baseline, plan.export_code)

    def write(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "original.py").write_text(self.baseline)
        (directory / "exports.py").write_text(self.exports)
        save_record(directory / "plan.json", self.plan.model_dump())


class SetupOutcome(StrictModel):
    disposition: Literal["tested", "blocked"]
    explanation: str = Field(min_length=1)
    source_adaptations: list[str]
    unresolved_assumptions: list[str]


@dataclass
class SetupRecipe:
    pyproject_toml: str
    system_packages: list[str]
    stage_inputs_sh: str


CANDIDATE_FILES = (
    "analysis.py",
    "pyproject.toml",
    "system-packages.json",
    "stage-inputs.sh",
    "inputs.json",
)
TEST_TOOL = {
    "type": "function",
    "function": {
        "name": "test_reference",
        "description": "Build the current recipe, stage original inputs, then test frozen exports plus analysis offline. Consumes one reference-test allowance even if setup fails.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


def inspect_candidate(directory: Path, prepared: PreparedReference):
    files = {name: (directory / name).read_bytes() for name in CANDIDATE_FILES}
    packages = json.loads(files["system-packages.json"])
    if not isinstance(packages, list) or any(not isinstance(p, str) for p in packages):
        raise ValueError("system-packages.json must be an array of strings")
    recipe = SetupRecipe(
        files["pyproject.toml"].decode(), packages, files["stage-inputs.sh"].decode()
    )
    validate_environment(recipe.pyproject_toml, recipe.system_packages)
    inventory = json.loads(files["inputs.json"])
    if (
        not isinstance(inventory, dict)
        or set(inventory) != {"files"}
        or not isinstance(inventory["files"], list)
    ):
        raise ValueError("inputs.json requires a files array")
    # Compile only. Runtime evidence and input byte checks come from the sandbox.
    script, _ = materialize(files["analysis.py"].decode(), prepared.plan)
    hashes = {name: digest(value) for name, value in files.items()}
    return recipe, script, hashes


class SetupSession:
    """Remote-only tool handlers; a successful claim requires current test evidence.

    remote implements upload, download, command(argv, seconds, label), and network.
    command returns a recorded process result plus log; no local execution fallback.
    """

    def __init__(self, *, prepared, remote, root, setup_seconds, reference_seconds, max_tests):
        if any(type(x) is not int or x < 1 for x in (setup_seconds, reference_seconds, max_tests)):
            raise ValueError("Explicit positive setup, reference and test allowances required")
        self.prepared, self.remote, self.root = prepared, remote, root
        self.setup_remaining = float(setup_seconds)
        self.reference_seconds, self.max_tests = reference_seconds, max_tests
        self.tests = 0
        self.shell_calls = 0
        self.last_pass = None
        self.root.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        frozen = self.root / "frozen"
        self.prepared.write(frozen)
        await self.remote.command(
            ["mkdir", "-p", "/work/frozen", "/work/setup", "/inputs", "/work/cache"],
            30,
            "initialize",
        )
        for name in ("original.py", "exports.py", "plan.json"):
            await self.remote.upload(frozen / name, "/work/frozen/" + name)
        await self.remote.upload(frozen / "original.py", "/work/setup/analysis.py")
        await self.remote.network(False)

    async def setup_command(self, argv, seconds, label):
        if type(seconds) is not int or seconds < 1:
            raise ValueError("Command timeout must be a positive integer")
        permitted = min(seconds, int(self.setup_remaining))
        if permitted < 1:
            raise TimeoutError("Cumulative setup tool time exhausted")
        started = time.monotonic()
        try:
            return await self.remote.command(argv, permitted, label)
        finally:
            self.setup_remaining -= time.monotonic() - started

    async def shell(self, command: str, timeout_sec: int = 120):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("A nonempty shell command is required")
        self.shell_calls += 1
        reply = await self.setup_command(
            ["sh", "-c", "cd /work/setup && " + command],
            timeout_sec,
            f"shell-{self.shell_calls}",
        )
        return json.dumps({**reply, "setup_seconds_remaining": self.setup_remaining})

    async def capture_candidate(self, directory):
        directory.mkdir(parents=True, exist_ok=False)
        probe = await self.remote.command(
            [
                "python",
                "-c",
                "from pathlib import Path; import sys; "
                + "paths = "
                + repr(["/work/setup/" + n for n in CANDIDATE_FILES])
                + "; "
                + "bad = [p for p in paths if not Path(p).is_file() or Path(p).is_symlink()]; "
                + "print(bad); sys.exit(bool(bad))",
            ],
            30,
            "candidate-files-" + str(time.time_ns()),
        )
        if probe["exit_code"]:
            raise ValueError("Missing or nonregular setup files: " + probe["log"])
        for name in CANDIDATE_FILES:
            await self.remote.download("/work/setup/" + name, directory / name)
        return inspect_candidate(directory, self.prepared)

    async def test_reference(self):
        if self.tests >= self.max_tests:
            return json.dumps({"error": "Reference-test allowance exhausted; report the blocker."})
        self.tests += 1
        self.last_pass = None
        directory = self.root / "trials" / str(self.tests)
        directory.mkdir(parents=True)
        record = {"test": self.tests, "status": "incomplete", "semantic_fidelity_validated": False}
        try:
            recipe, script, hashes = await self.capture_candidate(directory / "candidate")
            record["candidate_sha256"] = hashes
            import difflib

            changed = (directory / "candidate/analysis.py").read_text()
            (directory / "source.diff").write_text(
                "".join(
                    difflib.unified_diff(
                        self.prepared.baseline.splitlines(keepends=True),
                        changed.splitlines(keepends=True),
                        fromfile="original.py",
                        tofile="analysis.py",
                    )
                )
            )
            (directory / "reference.py").write_text(script)
            write_environment(directory, recipe, verify_inputs=False)
            await self.setup_command(
                ["sh", "-eu", "-c", "rm -rf /work/venv /work/environment; mkdir /work/environment"],
                30,
                f"reset-env-{self.tests}",
            )
            for name, target in [
                ("pyproject.toml", "environment/pyproject.toml"),
                ("stage-inputs.sh", "stage-inputs.sh"),
                ("setup.sh", "setup.sh"),
            ]:
                await self.remote.upload(directory / name, "/work/" + target)
            setup = await self.setup_command(
                ["sh", "-eu", "/work/setup.sh"], int(self.setup_remaining), f"setup-{self.tests}"
            )
            record["setup"] = setup
            if setup["exit_code"] != 0:
                record["status"] = "setup_failed"
                return json.dumps(record)
            # Staging must not rewrite the candidate after its snapshot was taken.
            _, _, after_setup = await self.capture_candidate(directory / "after-setup")
            if after_setup != hashes:
                raise ValueError("Setup changed its submitted candidate files")
            await self.remote.upload(
                directory / "candidate/inputs.json", "/work/declared-inputs.json"
            )
            await self.remote.helper(
                ["snapshot-inputs", "/work/declared-inputs.json", "/work/setup-inputs.json"],
                f"inputs-before-{self.tests}",
            )
            for name, source in [
                ("uv.lock", "environment/uv.lock"),
                ("environment.txt", "environment/environment.txt"),
                ("inputs-before.json", "setup-inputs.json"),
            ]:
                await self.remote.download("/work/" + source, directory / name)
            await self.remote.command(
                [
                    "sh",
                    "-eu",
                    "-c",
                    "rm -rf /work/run /work/outputs; mkdir /work/run /work/outputs",
                ],
                30,
                f"reset-run-{self.tests}",
            )
            await self.remote.upload(directory / "reference.py", "/work/reference.py")
            await self.remote.upload(self.root / "frozen/plan.json", "/work/plan.json")
            # Restore the receipt from host evidence; generated code cannot redefine it.
            await self.remote.upload(directory / "inputs-before.json", "/work/setup-inputs.json")
            await self.remote.network(True)
            try:
                run = await self.remote.command(
                    ["env", "MPLBACKEND=Agg", "/work/venv/bin/python", "/work/reference.py"],
                    self.reference_seconds,
                    f"reference-{self.tests}",
                    cwd="/work/run",
                )
                record["execution"] = run
                await self.remote.upload(
                    directory / "inputs-before.json", "/work/setup-inputs.json"
                )
                checked = await self.remote.helper(
                    ["verify-staging", "/work/setup-inputs.json"], f"inputs-after-{self.tests}"
                )
                record["inputs_after"] = checked
                await self.remote.upload(self.root / "frozen/plan.json", "/work/plan.json")
                inventory = await self.remote.helper(
                    ["inventory", "/work/plan.json"], f"inventory-{self.tests}"
                )
                record["artifacts"] = inventory
                for artifact in inventory["artifacts"]:
                    if artifact["exists"]:
                        target = directory / "outputs" / artifact["path"]
                        target.parent.mkdir(parents=True, exist_ok=True)
                        await self.remote.download("/work/outputs/" + artifact["path"], target)
                        with target.open("rb") as stream:
                            if (
                                hashlib.file_digest(stream, "sha256").hexdigest()
                                != artifact["sha256"]
                            ):
                                raise RuntimeError("Downloaded artifact hash mismatch")
                success = run["exit_code"] == 0 and inventory["declared_artifacts_present"]
                record["status"] = "reference_executed" if success else "reference_failed"
                if success:
                    self.last_pass = {
                        "hashes": hashes,
                        "test": self.tests,
                        "source_changed": changed != self.prepared.baseline,
                    }
            finally:
                # The adapter refuses policy changes after an uncertain command.
                await self.remote.network(False)
            return json.dumps(record)
        except (ValueError, SyntaxError) as exc:
            record.update(status="candidate_invalid", error=str(exc))
            return json.dumps(record)
        finally:
            save_record(directory / "result.json", record)

    async def validate_outcome(self, outcome: SetupOutcome):
        if outcome.disposition == "blocked":
            return
        if self.last_pass is None:
            raise ValueError("A tested outcome requires a successful controller test")
        _, _, current = await self.capture_candidate(self.root / "submission" / str(time.time_ns()))
        if current != self.last_pass["hashes"]:
            raise ValueError(
                "Candidate changed after its successful test; retest before submitting"
            )
        if self.last_pass["source_changed"] and not outcome.source_adaptations:
            raise ValueError("Explain source adaptations; the source diff is nonempty")
