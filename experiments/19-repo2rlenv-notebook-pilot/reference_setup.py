"""Tool-enabled setup contract and controller-owned offline test sequence.

No local scientific execution. Remote I/O and lifecycle are injected by the host.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field
from reference_environment import validate_environment, write_environment
from reference_protocol import ReferencePlan, StrictModel, materialize
from repo2rlenv.execution.lifecycle import save_record


class SetupBudgetExceeded(TimeoutError):
    """The tool was refused before dispatch because setup time is exhausted."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def import_inventory(source):
    """Annotate literal imports without importing a module or running the source."""
    rows = []

    def visit(node, context):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            rows.append(
                {
                    "line": node.lineno,
                    "statement": ast.get_source_segment(source, node),
                    "context": context,
                }
            )
        nested = context
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If, ast.Try)):
            nested = [*context, type(node).__name__]
        for child in ast.iter_child_nodes(node):
            visit(child, nested)

    visit(ast.parse(source), ["module"])
    return rows


def runtime_export_feedback(prepared, analysis: str, script: str, record: dict):
    """Identify a definite Python exception reached from the appended exports.

    This is execution feedback for an author, never scientific acceptance. Do
    not reinterpret resource failures, missing reports or source exceptions as
    an export defect. The setup runner has already closed offline execution and
    verified the staged input identities before calling this classifier.
    """
    run = record.get("execution", {})
    if (
        record.get("status") != "reference_failed"
        or type(run.get("exit_code")) is not int
        or run["exit_code"] != 1
        or record.get("inputs_after", {}).get("staged_inputs_verified") is not True
    ):
        return None
    if script != materialize(analysis, prepared.plan)[0]:
        raise ValueError("Runtime feedback does not match the assembled export script")
    if record.get("candidate_sha256", {}).get("analysis.py") != digest(analysis.encode()):
        raise ValueError("Runtime feedback does not match the captured analysis")
    log = run.get("log")
    if not isinstance(log, str) or "Traceback (most recent call last):" not in log:
        return None
    traceback = log.rsplit("Traceback (most recent call last):", 1)[1]
    frames = re.findall(
        r'^\s*File "/work/reference\.py", line (\d+), in <module>\s*$',
        traceback,
        re.MULTILINE,
    )
    export_start = (analysis + "\n\n").count("\n") + 1
    if len(frames) != 1 or int(frames[0]) < export_start:
        return None
    errors = re.findall(r"^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*Error):", traceback, re.MULTILINE)
    if not errors or errors[-1].rsplit(".", 1)[-1] in {"MemoryError", "TimeoutError"}:
        return None
    return {
        "kind": "runtime_export_exception",
        "exception_type": errors[-1],
        "analysis_sha256": digest(analysis.encode()),
        "reference_script_sha256": digest(script.encode()),
        "export_code_sha256": digest(prepared.exports.encode()),
        "export_start_line": export_start,
        "recorded_module_line": int(frames[0]),
        "execution": run,
        "staged_inputs_verified": True,
        "observation_scope": "Recorded execution log only; printed layouts may be partial. No new scientific computation or source repair is authorized.",
    }


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
    dependency_asset_review: str = ""


@dataclass
class SetupRecipe:
    pyproject_toml: str
    system_packages: list[str]
    stage_inputs_sh: str
    dependency_exclusions: dict


CANDIDATE_FILES = (
    "analysis.py",
    "pyproject.toml",
    "system-packages.json",
    "stage-inputs.sh",
    "inputs.json",
    "dependency-exclusions.json",
)
TEST_TOOL = {
    "type": "function",
    "function": {
        "name": "test_reference",
        "description": "Build the current recipe, stage original inputs, then test frozen exports plus analysis offline. A computation slot is consumed when the reference is dispatched, including failed or uncertain dispatches. Candidate validation, build and staging failures use the existing setup/time budgets without consuming a computation slot.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


def inspect_candidate(directory: Path, prepared: PreparedReference):
    from dependency_assets import validate_manifest

    files = {
        name: (directory / name).read_bytes()
        for name in CANDIDATE_FILES
        if name != "dependency-exclusions.json" or (directory / name).exists()
    }
    # Historical recipes had no exclusion declaration. Absence means no removal.
    files.setdefault("dependency-exclusions.json", b'{"files": []}\n')
    packages = json.loads(files["system-packages.json"])
    if not isinstance(packages, list) or any(not isinstance(p, str) for p in packages):
        raise ValueError("system-packages.json must be an array of strings")
    recipe = SetupRecipe(
        files["pyproject.toml"].decode(),
        packages,
        files["stage-inputs.sh"].decode(),
        validate_manifest(json.loads(files["dependency-exclusions.json"]), require_reason=True),
    )
    validate_environment(recipe.pyproject_toml, recipe.system_packages)
    inventory = json.loads(files["inputs.json"])
    if (
        not isinstance(inventory, dict)
        or set(inventory) != {"files"}
        or not isinstance(inventory["files"], list)
    ):
        raise ValueError("inputs.json requires a files array")
    seen = set()
    for index, item in enumerate(inventory["files"]):
        if not isinstance(item, dict) or any(
            not isinstance(item.get(key), str) or not item[key].strip()
            for key in ("local_path", "source")
        ):
            raise ValueError(
                f"inputs.json file {index} needs nonempty local_path and source strings"
            )
        path = Path(item["local_path"])
        if (
            not path.is_absolute()
            or ".." in path.parts
            or not any(path.is_relative_to(root) for root in (Path("/inputs"), Path("/work/cache")))
            or str(path) in seen
        ):
            raise ValueError(
                f"inputs.json file {index} needs a unique absolute file path under "
                "/inputs or /work/cache, without parent traversal"
            )
        seen.add(str(path))
    # Compile only. Runtime evidence and input byte checks come from the sandbox.
    analysis = files["analysis.py"].decode()
    script, _ = materialize(analysis, prepared.plan)

    def imports(source):
        return [
            ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

    if imports(analysis) != imports(prepared.baseline):
        raise ValueError(
            "Analysis imports changed. Install missing dependencies in the environment; "
            "do not repair source-code imports. Report the original source blocker."
        )
    hashes = {name: digest(value) for name, value in files.items()}
    return recipe, script, hashes


class SetupSession:
    """Remote-only tool handlers; a successful claim requires current test evidence.

    remote implements upload, download, command(argv, seconds, label), and network.
    command returns a recorded process result plus log; no local execution fallback.
    """

    def __init__(
        self,
        *,
        prepared,
        remote,
        root,
        setup_seconds,
        reference_seconds,
        max_tests,
        repair_exports=None,
    ):
        if any(type(x) is not int or x < 1 for x in (setup_seconds, reference_seconds, max_tests)):
            raise ValueError("Explicit positive setup, reference and test allowances required")
        self.prepared, self.remote, self.root = prepared, remote, root
        self.setup_remaining = float(setup_seconds)
        self.reference_seconds, self.max_tests = reference_seconds, max_tests
        self.tests = 0
        self.test_requests = 0
        self.shell_calls = 0
        self.last_pass = None
        self.repair_exports = repair_exports
        self.effective_preparation = None
        self.frozen = self.root / "frozen"
        self.root.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        frozen = self.frozen
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
            raise SetupBudgetExceeded("Cumulative setup tool time exhausted; submit blocked.")
        started = time.monotonic()
        try:
            return await self.remote.command(argv, permitted, label)
        finally:
            self.setup_remaining -= time.monotonic() - started

    async def shell(self, command: str, timeout_sec: int = 120):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("A nonempty shell command is required")
        self.shell_calls += 1
        try:
            reply = await self.setup_command(
                ["sh", "-c", "cd /work/setup && " + command],
                timeout_sec,
                f"shell-{self.shell_calls}",
            )
        except SetupBudgetExceeded as error:
            return json.dumps(
                {"error": str(error), "setup_seconds_remaining": self.setup_remaining}
            )
        return json.dumps(
            {
                **reply,
                "setup_seconds_remaining": self.setup_remaining,
                "process_policy": "Foreground setup and targeted inspection only; durable background jobs are unsupported. Use test_reference for the complete offline analysis.",
            }
        )

    async def capture_candidate(self, directory):
        directory.mkdir(parents=True, exist_ok=False)
        probe = await self.remote.command(
            [
                "python",
                "-c",
                "from pathlib import Path; import sys; "
                + "declaration = Path('/work/setup/dependency-exclusions.json'); "
                + "declaration.write_text('{\"files\": []}\\n') if not declaration.exists() else None; "
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
        self.test_requests += 1
        self.last_pass = None
        directory = self.root / "trials" / str(self.test_requests)
        directory.mkdir(parents=True)
        record = {
            "test": self.test_requests,
            "reference_tests_used": self.tests,
            "reference_tests_remaining": self.max_tests - self.tests,
            "status": "incomplete",
            "semantic_fidelity_validated": False,
        }
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
                [
                    "sh",
                    "-eu",
                    "-c",
                    "rm -rf /work/venv /work/environment /work/cache /inputs; "
                    "mkdir -p /work/environment /work/cache /inputs",
                ],
                30,
                f"reset-env-{self.test_requests}",
            )
            for name, target in [
                ("pyproject.toml", "environment/pyproject.toml"),
                ("stage-inputs.sh", "stage-inputs.sh"),
                ("setup.sh", "setup.sh"),
                ("dependency-exclusions.json", "environment/dependency-exclusions.json"),
                ("dependency_assets.py", "dependency_assets.py"),
            ]:
                await self.remote.upload(directory / name, "/work/" + target)
            setup = await self.setup_command(
                ["sh", "-eu", "/work/setup.sh"],
                int(self.setup_remaining),
                f"setup-{self.test_requests}",
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
            staged = await self.remote.helper(
                ["snapshot-inputs", "/work/declared-inputs.json", "/work/setup-inputs.json"],
                f"inputs-before-{self.test_requests}",
            )
            if "input_validation_error" in staged:
                record.update(status="candidate_invalid", error=staged["input_validation_error"])
                return json.dumps(record)
            record["input_observations"] = staged
            for name, source in [
                ("uv.lock", "environment/uv.lock"),
                ("environment.txt", "environment/environment.txt"),
                ("inputs-before.json", "setup-inputs.json"),
                (
                    "dependency-exclusions-applied.json",
                    "environment/dependency-exclusions-applied.json",
                ),
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
                f"reset-run-{self.test_requests}",
            )
            await self.remote.upload(directory / "reference.py", "/work/reference.py")
            await self.remote.upload(self.frozen / "plan.json", "/work/plan.json")
            # Restore the receipt from host evidence; generated code cannot redefine it.
            await self.remote.upload(directory / "inputs-before.json", "/work/setup-inputs.json")
            await self.remote.network(True)
            try:
                # A rejected manifest or failed build never reached reference
                # dispatch. Those calls retain evidence and consume setup/time
                # budgets, but do not spend a full computation attempt.
                self.tests += 1
                record.update(
                    reference_tests_used=self.tests,
                    reference_tests_remaining=self.max_tests - self.tests,
                )
                run = await self.remote.command(
                    ["env", "MPLBACKEND=Agg", "/work/venv/bin/python", "/work/reference.py"],
                    self.reference_seconds,
                    f"reference-{self.test_requests}",
                    cwd="/work/run",
                )
                record["execution"] = run
                await self.remote.upload(
                    directory / "inputs-before.json", "/work/setup-inputs.json"
                )
                checked = await self.remote.helper(
                    ["verify-staging", "/work/setup-inputs.json"],
                    f"inputs-after-{self.test_requests}",
                )
                record["inputs_after"] = checked
                await self.remote.upload(self.frozen / "plan.json", "/work/plan.json")
                inventory = await self.remote.helper(
                    ["inventory", "/work/plan.json"], f"inventory-{self.test_requests}"
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
                    # Actual installed evidence, not an assumed wheel layout.
                    # The existing GLM setup worker judges relevance/unused
                    # status and can use its remaining test after exclusions.
                    save_record(directory / "output-inventory.json", inventory["artifacts"])
                    await self.remote.upload(
                        directory / "output-inventory.json", "/work/output-inventory.json"
                    )
                    await self.remote.upload(
                        directory / "dependency_assets.py", "/work/dependency_assets.py"
                    )
                    audit = await self.setup_command(
                        [
                            "/work/venv/bin/python",
                            "/work/dependency_assets.py",
                            "inspect",
                            "/work/output-inventory.json",
                            "/work/dependency-assets.json",
                        ],
                        120,
                        f"dependency-assets-{self.test_requests}",
                    )
                    save_record(directory / "dependency-assets-command.json", audit)
                    if audit["exit_code"]:
                        raise RuntimeError("Installed dependency-asset inspection failed")
                    await self.remote.download(
                        "/work/dependency-assets.json", directory / "dependency-assets.json"
                    )
                    catalog = json.loads((directory / "dependency-assets.json").read_text())
                    summary = catalog["summary"]
                    save_record(directory / "dependency-assets-summary.json", summary)
                    record["dependency_assets"] = {
                        **summary,
                        "full_catalog": "/work/dependency-assets.json",
                        "catalog_sha256": digest(
                            (directory / "dependency-assets.json").read_bytes()
                        ),
                    }
                    self.last_pass = {
                        "hashes": hashes,
                        "test": self.test_requests,
                        "source_changed": changed != self.prepared.baseline,
                        "dependency_asset_candidates": summary["candidate_files"],
                    }
            finally:
                # The adapter refuses policy changes after an uncertain command.
                await self.remote.network(False)
            if self.repair_exports is not None and self.tests < self.max_tests:
                feedback = runtime_export_feedback(self.prepared, changed, script, record)
                if feedback is not None:
                    # Persist the original failed test before any model or remote mutation.
                    save_record(directory / "result.json", record)
                    save_record(directory / "original-execution-result.json", record)
                    save_record(directory / "runtime-export-feedback.json", feedback)
                    repair = {"status": "started"}
                    save_record(directory / "runtime-export-repair.json", repair)
                    callback, self.repair_exports = self.repair_exports, None
                    try:
                        effective = await callback(feedback)
                        if effective is None:
                            repair["status"] = "no_preparation_repair_remaining"
                        else:
                            revised = PreparedReference.load(effective)
                            if (
                                revised.baseline != self.prepared.baseline
                                or revised.context["source"] != self.prepared.context["source"]
                                or revised.plan.artifacts != self.prepared.plan.artifacts
                                or revised.plan.excluded_outputs
                                != self.prepared.plan.excluded_outputs
                            ):
                                raise ValueError(
                                    "Runtime repair changed the source or endpoint scope"
                                )
                            frozen = self.root / "frozen-runtime-repair"
                            if frozen.exists():
                                raise ValueError("Runtime repair has already been materialized")
                            revised.write(frozen)
                            for name in ("original.py", "exports.py", "plan.json"):
                                await self.remote.upload(frozen / name, "/work/frozen/" + name)
                            self.prepared, self.frozen = revised, frozen
                            self.effective_preparation = effective
                            repair.update(
                                status="exports_corrected_requires_retest",
                                export_code_sha256=digest(revised.exports.encode()),
                            )
                    except BaseException as error:
                        repair.update(status="incomplete", error_type=type(error).__name__)
                        raise
                    finally:
                        save_record(directory / "runtime-export-repair.json", repair)
                    return json.dumps({**record, "runtime_export_repair": repair})
            return json.dumps(record)
        except SetupBudgetExceeded as exc:
            record.update(status="setup_budget_exhausted", error=str(exc))
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
        if (
            self.last_pass.get("dependency_asset_candidates", 0)
            and not outcome.dependency_asset_review.strip()
        ):
            raise ValueError(
                "Review actual installed asset candidates, requested-answer exposure and exclusions before submitting; differing bytes alone do not prove safety"
            )
