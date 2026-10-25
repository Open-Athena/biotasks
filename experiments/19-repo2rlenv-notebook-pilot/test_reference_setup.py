"""Setup-stage boundaries, using synthetic inputs and an in-memory remote worker."""

import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest
from reference_protocol import ReferencePlan
from reference_remote import snapshot_inputs, verify_staging
from reference_setup import (
    TEST_TOOL,
    PreparedReference,
    SetupOutcome,
    SetupSession,
    direct_source_invocation,
)
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget
from run_reference_setup import check_config
from test_design_stage import response

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger

HERE = Path(__file__).parent


def prepared():
    return PreparedReference(
        {},
        ReferencePlan(
            disposition="prepare",
            explanation="fixture",
            export_code="print(result)\n",
            artifacts=[
                {"path": "result.txt", "description": "fixture", "source_evidence": "result"}
            ],
            excluded_outputs=[],
            unresolved_assumptions=[],
        ),
        "result = 1\n",
        "print(result)\n",
    )


class FakeRemote:
    def __init__(self, *, setup_failure=False, missing_output=False, mutated_input=False):
        self.files = {
            "/work/setup/analysis.py": b"result = 1\n",
            "/work/setup/pyproject.toml": b'[project]\nname="fixture"\nversion="0.1"\nrequires-python=">=3.13"\ndependencies=[]\n',
            "/work/setup/system-packages.json": b"[]",
            "/work/setup/stage-inputs.sh": b"",
            "/work/setup/inputs.json": b'{"files": []}',
            "/work/setup/dependency-exclusions.json": b'{"files": []}\n',
        }
        self.events = []
        self.blocked = False
        self.uncertain = False
        self.setup_failure = setup_failure
        self.missing_output = missing_output
        self.mutated_input = mutated_input
        self.manual_packages = {"base-runtime"}

    async def upload(self, local, remote):
        self.files[remote] = local.read_bytes()

    async def download(self, remote, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(self.files[remote])

    async def command(self, argv, seconds, label, *, cwd="/work"):
        self.events.append((label, self.blocked, cwd))
        if argv == ["apt-mark", "showmanual"]:
            return {"exit_code": 0, "log": "\n".join(sorted(self.manual_packages)) + "\n"}
        if label.startswith("dependency-assets-"):
            assert argv[-1] == "/work/frozen/original.py"
            assert argv[-1] in self.files
            self.files["/work/dependency-assets.json"] = json.dumps(
                {
                    "files": [],
                    "summary": {
                        "candidate_files": 0,
                        "priority_matches": [],
                        "installed_files_inspected": 0,
                        "scope": "Synthetic empty environment",
                    },
                }
            ).encode()
        if label.startswith("reference-"):
            assert self.blocked
            assert cwd == "/work/run"
            self.files["/work/outputs/result.txt"] = b"1\n"
        if label.startswith("setup-"):
            self.files["/work/environment/uv.lock"] = b"version = 1\n"
            self.files["/work/environment/environment.txt"] = b""
            self.files["/work/environment/dependency-exclusions-applied.json"] = (
                b'{"files": [], "excluded_files_absent": true}\n'
            )
            self.files["/work/setup-inputs.json"] = b'{"files": []}'
            if self.setup_failure:
                return {"exit_code": 1, "log": "Missing dependency"}
        return {"exit_code": 0, "log": ""}

    async def network(self, blocked):
        self.events.append(("network", blocked, None))
        self.blocked = blocked

    async def helper(self, args, label):
        if args[0] == "snapshot-inputs":
            self.files["/work/setup-inputs.json"] = b'{"files": []}'
            return {"files": []}
        assert self.blocked
        if args[0] == "verify-staging":
            if self.mutated_input:
                raise RuntimeError("Input checksum changed")
            return {"staged_inputs_verified": True, "files": 0}
        data = self.files["/work/outputs/result.txt"]
        return {
            "artifacts": [
                {
                    "path": "result.txt",
                    "exists": not self.missing_output,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ],
            "declared_artifacts_present": not self.missing_output,
        }


def session(tmp_path, remote=None):
    return SetupSession(
        prepared=prepared(),
        remote=remote or FakeRemote(),
        root=tmp_path,
        setup_seconds=60,
        reference_seconds=10,
        max_tests=1,
    )


@pytest.mark.parametrize("installed_by_staging", [False, True])
def test_unrecorded_exploratory_packages_return_feedback_before_scientific_dispatch(
    tmp_path, installed_by_staging
):
    class Packages(FakeRemote):
        async def command(self, argv, seconds, label, **kwargs):
            if installed_by_staging and label.startswith("setup-"):
                self.manual_packages.add("additional-runtime:amd64")
            return await super().command(argv, seconds, label, **kwargs)

    async def run():
        remote = Packages()
        s = session(tmp_path, remote)
        await s.initialize()
        baseline = json.loads((tmp_path / "base-system-packages.json").read_text())
        assert baseline["manual_packages"] == ["base-runtime"]
        if not installed_by_staging:
            remote.manual_packages.add("additional-runtime:amd64")
        result = json.loads(await s.test_reference())
        assert result["status"] == "candidate_invalid"
        assert "additional-runtime" in result["error"]
        assert s.tests == 0 and s.last_pass is None
        assert not any(label.startswith("reference-") for label, _, _ in remote.events)
        phase = "after-setup" if installed_by_staging else "before-setup"
        audit = json.loads((tmp_path / f"trials/1/system-package-audit-{phase}.json").read_text())
        assert audit["undeclared_introduced_packages"] == ["additional-runtime"]
        # A corrected declaration, including a version/architecture, can use
        # the same still-unspent computation slot. No scientific source edit.
        original = remote.files["/work/setup/analysis.py"]
        remote.files["/work/setup/system-packages.json"] = b'["additional-runtime:amd64=1:2.0"]'
        result = json.loads(await s.test_reference())
        assert result["status"] == "reference_executed" and s.tests == 1
        assert remote.files["/work/setup/analysis.py"] == original

    asyncio.run(run())


def test_package_inventory_fault_is_not_a_validated_recipe(tmp_path):
    class BrokenInventory(FakeRemote):
        async def command(self, argv, seconds, label, **kwargs):
            if argv == ["apt-mark", "showmanual"]:
                return {"exit_code": 1, "log": "inventory unavailable"}
            return await super().command(argv, seconds, label, **kwargs)

    async def run():
        s = session(tmp_path, BrokenInventory())
        with pytest.raises(RuntimeError, match="installation state"):
            await s.initialize()
        assert s.tests == 0 and s.last_pass is None

    asyncio.run(run())


def test_import_inventory_describes_conditional_imports_without_executing():
    from reference_setup import import_inventory

    source = "import never_installed\nif False:\n    from absent_package import Draw\ndef f():\n    import another_absent\n"
    assert import_inventory(source) == [
        {"line": 1, "statement": "import never_installed", "context": ["module"]},
        {"line": 3, "statement": "from absent_package import Draw", "context": ["module", "If"]},
        {"line": 5, "statement": "import another_absent", "context": ["module", "FunctionDef"]},
    ]


def test_actual_asset_candidates_reach_existing_worker_and_require_review(tmp_path):
    class Assets(FakeRemote):
        async def command(self, argv, seconds, label, **kwargs):
            reply = await super().command(argv, seconds, label, **kwargs)
            if label.startswith("dependency-assets-"):
                entry = {
                    "distribution": "example",
                    "path": "example/tests/expected.txt",
                    "sha256": "a" * 64,
                    "bytes": 10,
                    "eligible_for_declared_removal": True,
                }
                self.files["/work/dependency-assets.json"] = json.dumps(
                    {
                        "files": [entry],
                        "summary": {
                            "candidate_files": 1,
                            "priority_matches": [entry],
                            "scope": "Synthetic installed-file observations",
                        },
                    }
                ).encode()
            return reply

    async def exercise():
        s = session(tmp_path, Assets())
        await s.initialize()
        result = json.loads(await s.test_reference())
        assert result["dependency_assets"]["priority_matches"][0]["distribution"] == "example"
        assert (tmp_path / "trials/1/dependency-assets.json").is_file()
        with pytest.raises(ValueError, match="Review actual installed"):
            await s.validate_outcome(successful_outcome())
        reviewed = successful_outcome().model_copy(
            update={
                "dependency_asset_review": "Inspected actual catalog and source usage; candidate is an input, not an answer to the requested result."
            }
        )
        await s.validate_outcome(reviewed)
        assert s.tests == 1  # Metadata inspection/review is not another reference run.

    asyncio.run(exercise())


@pytest.mark.parametrize("trailing_newline", [False, True])
@pytest.mark.parametrize("phase", ["source", "export", "resource", "missing_trace"])
def test_runtime_export_feedback_requires_definite_append_phase_evidence(
    tmp_path, phase, trailing_newline
):
    from reference_protocol import materialize
    from reference_setup import runtime_export_feedback

    analysis = "result = 1" + ("\n" if trailing_newline else "")
    exports = "def save(value):\n    return value.missing_attribute\nsave(result)\n"
    current = prepared()
    if phase == "source":
        analysis = "result = object().missing_attribute" + ("\n" if trailing_newline else "")
    plan = current.plan.model_copy(update={"export_code": exports})
    current = replace(current, baseline=analysis, exports=exports, plan=plan)
    script, _ = materialize(analysis, plan)
    path = tmp_path / "reference.py"
    path.write_text(script)
    execution = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    log = execution.stderr.replace(str(path), "/work/reference.py")
    record = {
        "status": "reference_failed",
        "candidate_sha256": {"analysis.py": hashlib.sha256(analysis.encode()).hexdigest()},
        "inputs_after": {"staged_inputs_verified": True},
        "execution": {"exit_code": execution.returncode, "log": log},
    }
    if phase == "resource":
        record["execution"]["exit_code"] = 137
    if phase == "missing_trace":
        record["execution"]["log"] = "No execution traceback was received."
    feedback = runtime_export_feedback(current, analysis, script, record)
    if phase != "export":
        assert feedback is None
        return
    assert feedback["exception_type"] == "AttributeError"
    assert feedback["recorded_module_line"] >= feedback["export_start_line"]
    assert feedback["export_code_sha256"] == hashlib.sha256(exports.encode()).hexdigest()
    record["inputs_after"]["staged_inputs_verified"] = False
    assert runtime_export_feedback(current, analysis, script, record) is None
    record["inputs_after"]["staged_inputs_verified"] = True
    record["candidate_sha256"]["analysis.py"] = "0" * 64
    with pytest.raises(ValueError, match="captured analysis"):
        runtime_export_feedback(current, analysis, script, record)


@pytest.mark.parametrize("mode", ["repair", "spent", "rejected", "last_test", "source", "resource"])
def test_runtime_repair_preserves_failed_trial_and_requires_remaining_test(tmp_path, mode):
    from reference_protocol import materialize
    from repo2rlenv.execution.lifecycle import save_record

    original = prepared()
    original = replace(
        original,
        context={
            "baseline_script": original.baseline,
            "source": {"source_sha256": "fixture"},
            "conversion": {
                "source_sha256": "fixture",
                "script_sha256": hashlib.sha256(original.baseline.encode()).hexdigest(),
            },
        },
    )
    exports = "raise TypeError('Synthetic export failure')\n"
    original = replace(
        original, exports=exports, plan=original.plan.model_copy(update={"export_code": exports})
    )
    script = materialize(original.baseline, original.plan)[0]
    reference = tmp_path / "reference.py"
    reference.write_text(script)
    executed = subprocess.run([sys.executable, str(reference)], capture_output=True, text=True)
    log = executed.stderr.replace(str(reference), "/work/reference.py")
    if mode == "source":
        log = log.replace(f"line {len(original.baseline.splitlines()) + 3}", "line 1")

    class ExportRemote(FakeRemote):
        async def command(self, argv, seconds, label, *, cwd="/work"):
            reply = await super().command(argv, seconds, label, cwd=cwd)
            if label == "reference-1":
                return {"exit_code": 137 if mode == "resource" else 1, "log": log}
            return reply

    remote = ExportRemote()
    calls = []

    async def repair(feedback):
        assert not remote.blocked  # Offline execution has closed before model feedback.
        assert s.tests == 1
        assert json.loads((s.root / "trials/1/result.json").read_text())["execution"]["log"] == log
        calls.append(feedback)
        if mode == "rejected":
            from reference_protocol import RuntimeExportRepairRejected

            raise RuntimeExportRepairRejected("Synthetic invalid repair response")
        if mode == "spent":
            return None
        revised = prepared().plan
        fixed = tmp_path / "corrected"
        (fixed / "prepare").mkdir(parents=True)
        save_record(fixed / "prepare/input.json", original.context)
        save_record(fixed / "plan.json", revised.model_dump())
        source, diff = materialize(original.baseline, revised)
        (fixed / "exports.py").write_text(revised.export_code)
        (fixed / "reference.py").write_text(source)
        (fixed / "source.diff").write_text(diff)
        return fixed

    s = SetupSession(
        prepared=original,
        remote=remote,
        root=tmp_path / "setup",
        setup_seconds=60,
        reference_seconds=10,
        max_tests=1 if mode == "last_test" else 2,
        repair_exports=repair,
    )

    async def run():
        await s.initialize()
        initial = (s.root / "frozen/exports.py").read_bytes()
        reply = json.loads(await s.test_reference())
        assert reply["status"] == "reference_failed"
        saved = (s.root / "trials/1/result.json").read_bytes()
        if mode == "repair":
            assert reply["runtime_export_repair"]["status"] == "exports_corrected_requires_retest"
            assert s.last_pass is None and s.tests == 1
            assert (s.root / "frozen/exports.py").read_bytes() == initial
            assert s.frozen.name == "frozen-runtime-repair"
            assert json.loads(await s.test_reference())["status"] == "reference_executed"
            assert s.tests == 2 and s.last_pass["test"] == 2
            assert "exhausted" in json.loads(await s.test_reference())["error"]
        else:
            assert s.frozen.name == "frozen" and s.effective_preparation is None
            if mode == "rejected":
                assert reply["runtime_export_repair"]["status"] == "preparation_repair_rejected"
                assert (
                    reply["runtime_export_repair"]["further_preparation_repair_available"] is False
                )
                assert s.tests == 1 and s.repair_exports is None and s.last_pass is None
        assert (s.root / "trials/1/result.json").read_bytes() == saved
        assert len(calls) == (1 if mode in {"repair", "spent", "rejected"} else 0)

    asyncio.run(run())


def test_controlled_setup_cannot_reuse_exploratory_inputs(tmp_path):
    work, inputs = tmp_path / "work", tmp_path / "inputs"
    for directory in (work / "cache", work / "venv", work / "environment", inputs):
        directory.mkdir(parents=True)
        (directory / "exploratory-only").write_text("not reproducible")
    outside = tmp_path / "outside.txt"
    outside.write_text("preserve")
    (work / "cache/link").symlink_to(outside)
    (work / "setup").mkdir()
    (work / "setup/recipe").write_text("preserve candidate")

    class FreshRemote(FakeRemote):
        async def command(self, argv, seconds, label, *, cwd="/work"):
            if label.startswith("reset-env-"):
                command = argv[-1].replace("/work", str(work)).replace("/inputs", str(inputs))
                subprocess.run(["sh", "-eu", "-c", command], check=True, timeout=10)
            if label.startswith("setup-"):
                assert list(inputs.iterdir()) == []
                assert list((work / "cache").iterdir()) == []
                assert not (work / "venv").exists()
                assert outside.read_text() == "preserve"
                assert (work / "setup/recipe").read_text() == "preserve candidate"
            return await super().command(argv, seconds, label, cwd=cwd)

    async def run():
        s = session(tmp_path / "records", FreshRemote())
        await s.initialize()
        assert json.loads(await s.test_reference())["status"] == "reference_executed"

    asyncio.run(run())


@pytest.mark.parametrize(
    "files",
    [
        ["not a file record"],
        [{"local_path": "/inputs/data", "url": "https://example.org/data"}],
        [{"local_path": "/inputs/data", "source": " "}],
        [{"local_path": "relative/data", "source": "fixture"}],
        [{"local_path": "/work/setup/data", "source": "fixture"}],
        [{"local_path": "/inputs/../data", "source": "fixture"}],
        [{"local_path": "/inputs/data", "source": "fixture"}] * 2,
    ],
)
def test_invalid_input_inventory_returns_feedback_before_build(tmp_path, files):
    async def run():
        remote = FakeRemote()
        s = session(tmp_path, remote)
        await s.initialize()
        remote.files["/work/setup/inputs.json"] = json.dumps({"files": files}).encode()
        result = json.loads(await s.test_reference())
        assert result["status"] == "candidate_invalid"
        assert "inputs.json file" in result["error"]
        assert s.last_pass is None
        assert not any(
            label.startswith(("setup-", "reference-", "reset-env-")) for label, *_ in remote.events
        )

    asyncio.run(run())


def test_missing_staged_file_can_be_repaired_by_worker_within_existing_tests(tmp_path):
    class MissingInput(FakeRemote):
        invalid = True

        async def helper(self, args, label):
            if args[0] == "snapshot-inputs" and self.invalid:
                return {"input_validation_error": "Missing declared staged file"}
            return await super().helper(args, label)

    async def run():
        remote = MissingInput()
        s = SetupSession(
            prepared=prepared(),
            remote=remote,
            root=tmp_path,
            setup_seconds=60,
            reference_seconds=10,
            max_tests=1,
        )
        await s.initialize()
        result = json.loads(await s.test_reference())
        assert result["status"] == "candidate_invalid"
        assert "Missing declared" in result["error"]
        assert s.last_pass is None
        assert s.tests == 0
        assert not any(label.startswith("reference-") for label, *_ in remote.events)
        # No reference was dispatched; the first computation is still available.
        remote.invalid = False
        assert json.loads(await s.test_reference())["status"] == "reference_executed"
        assert s.last_pass["test"] == 2
        assert s.tests == 1

    asyncio.run(run())


@pytest.mark.parametrize("defect", ["manifest", "setup"])
def test_preexecution_failures_keep_computation_slot_and_preserve_each_trial(tmp_path, defect):
    async def run():
        remote = FakeRemote(setup_failure=defect == "setup")
        s = session(tmp_path, remote)
        await s.initialize()
        if defect == "manifest":
            remote.files["/work/setup/inputs.json"] = b'{"files": [{}]}'
        for number in (1, 2):
            result = json.loads(await s.test_reference())
            assert result["status"] == (
                "candidate_invalid" if defect == "manifest" else "setup_failed"
            )
            assert result["test"] == number
            assert result["reference_tests_used"] == 0
            assert result["reference_tests_remaining"] == 1
            assert s.tests == 0 and s.last_pass is None
            assert (tmp_path / f"trials/{number}/result.json").is_file()
        remote.setup_failure = False
        remote.files["/work/setup/inputs.json"] = b'{"files": []}'
        result = json.loads(await s.test_reference())
        assert result["status"] == "reference_executed"
        assert result["test"] == 3 and result["reference_tests_used"] == 1
        assert s.last_pass["test"] == 3 and s.tests == 1
        assert sum(label.startswith("reference-") for label, *_ in remote.events) == 1
        before = list(remote.events)
        assert "exhausted" in json.loads(await s.test_reference())["error"]
        assert remote.events == before and s.test_requests == 3

    asyncio.run(run())


def test_failed_computation_uses_a_slot_and_no_third_reference_is_dispatched(tmp_path):
    class FailedReference(FakeRemote):
        failed = True

        async def command(self, argv, seconds, label, *, cwd="/work"):
            result = await super().command(argv, seconds, label, cwd=cwd)
            if label.startswith("reference-") and self.failed:
                result["exit_code"] = 1
            return result

    async def run():
        remote = FailedReference()
        s = SetupSession(
            prepared=prepared(),
            remote=remote,
            root=tmp_path,
            setup_seconds=60,
            reference_seconds=10,
            max_tests=2,
        )
        await s.initialize()
        result = json.loads(await s.test_reference())
        assert result["status"] == "reference_failed" and s.tests == 1
        remote.failed = False
        result = json.loads(await s.test_reference())
        assert result["status"] == "reference_executed" and s.tests == 2
        before = list(remote.events)
        assert "exhausted" in json.loads(await s.test_reference())["error"]
        assert remote.events == before
        assert sum(label.startswith("reference-") for label, *_ in remote.events) == 2

    asyncio.run(run())


def test_uncertain_reference_dispatch_does_not_refund_a_computation_slot(tmp_path):
    class LostReference(FakeRemote):
        async def command(self, argv, seconds, label, *, cwd="/work"):
            if label.startswith("reference-"):
                raise RuntimeError("Uncertain reference completion")
            return await super().command(argv, seconds, label, cwd=cwd)

    async def run():
        remote = LostReference()
        s = session(tmp_path, remote)
        await s.initialize()
        with pytest.raises(RuntimeError, match="Uncertain reference"):
            await s.test_reference()
        assert s.tests == 1 and s.last_pass is None
        assert "exhausted" in json.loads(await s.test_reference())["error"]

    asyncio.run(run())


def test_uncertain_reference_preserves_provider_error_and_stays_offline(tmp_path):
    class ProviderError(ConnectionError):
        pass

    failure = ProviderError("synthetic lost reference response")

    class LostReference(FakeRemote):
        async def command(self, argv, seconds, label, *, cwd="/work"):
            if label.startswith("reference-"):
                self.uncertain = True
                raise failure
            return await super().command(argv, seconds, label, cwd=cwd)

        async def network(self, blocked):
            if self.uncertain:
                raise RuntimeError("uncertain operation blocks policy changes")
            await super().network(blocked)

    async def run():
        remote = LostReference()
        s = session(tmp_path, remote)
        await s.initialize()
        with pytest.raises(ProviderError) as raised:
            await s.test_reference()
        assert raised.value is failure
        assert remote.blocked and remote.uncertain
        assert remote.events[-1] == ("network", True, None)
        assert s.tests == 1 and s.last_pass is None
        record = json.loads((tmp_path / "trials/1/result.json").read_text())
        assert record["status"] == "incomplete"
        assert record["reference_tests_used"] == 1
        assert "exhausted" in json.loads(await s.test_reference())["error"]

    asyncio.run(run())


def test_exhausted_setup_returns_feedback_without_dispatch_or_more_computations(tmp_path):
    async def run():
        remote = FakeRemote()
        s = session(tmp_path, remote)
        await s.initialize()
        s.setup_remaining = 0
        before = list(remote.events)
        answer = json.loads(await s.shell("must not run"))
        assert "exhausted" in answer["error"] and remote.events == before
        answer = json.loads(await s.test_reference())
        assert answer["status"] == "setup_budget_exhausted"
        assert s.tests == 0 and s.last_pass is None
        assert not any(label.startswith(("setup-", "reference-")) for label, *_ in remote.events)

    asyncio.run(run())


@pytest.mark.parametrize(
    "command",
    [
        "python /work/setup/analysis.py",
        "MPLBACKEND=Agg /tmp/venv/bin/python3.13 analysis.py > /tmp/check.log",
        "ls /inputs; cd /tmp && python -W ignore /work/run/reference.py; echo done",
        "cd /tmp\npython original.py",
        "env FOO=bar python exports.py",
        "uv run python reference.py",
        "uv run --python 3.13 analysis.py",
        "./analysis.py",
        "bash -c 'python /work/setup/analysis.py'",
    ],
)
def test_literal_source_launches_are_refused_by_role_not_seed(command):
    assert direct_source_invocation(command) in {
        "analysis.py",
        "original.py",
        "reference.py",
        "exports.py",
    }


@pytest.mark.parametrize(
    "command",
    [
        "cat analysis.py; grep import original.py",
        "python -c \"import json; print(open('analysis.py').read())\"",
        "python -m py_compile analysis.py",
        "python -c 'import numpy; print(numpy.__version__)'",
        "uv sync --project /work/setup",
        "printf '%s' python analysis.py",
    ],
)
def test_setup_inspection_and_static_compilation_remain_available(command):
    assert direct_source_invocation(command) is None


def test_source_shell_refusal_is_recorded_without_dispatch_or_consuming_test(tmp_path):
    async def run():
        remote = FakeRemote()
        s = session(tmp_path, remote)
        before = list(remote.events)
        remaining = s.setup_remaining
        answer = json.loads(await s.shell("python /work/setup/analysis.py"))
        assert answer["dispatched"] is False
        assert answer["reference_test_consumed"] is False
        assert "test_reference" in answer["error"]
        assert remote.events == before and s.setup_remaining == remaining
        assert s.tests == s.test_requests == 0 and s.last_pass is None
        assert json.loads((tmp_path / "shell-policy/0001.json").read_text()) == answer
        # A refused attempt does not disable ordinary setup inspection.
        assert json.loads(await s.shell("python -c 'import json'"))["exit_code"] == 0
        assert remote.events[-1][0] == "shell-2"

    asyncio.run(run())


def test_remote_timeout_is_not_misreported_as_safe_budget_feedback(tmp_path):
    class Uncertain(FakeRemote):
        async def command(self, *args, **kwargs):
            raise TimeoutError("Provider completion uncertain")

    async def run():
        s = session(tmp_path, Uncertain())
        with pytest.raises(TimeoutError, match="completion uncertain"):
            await s.shell("one action only")

    asyncio.run(run())


def test_snapshot_controller_fault_is_not_worker_feedback(tmp_path):
    class BrokenHelper(FakeRemote):
        async def helper(self, args, label):
            raise RuntimeError("unexpected controller failure")

    async def run():
        s = session(tmp_path, BrokenHelper())
        await s.initialize()
        with pytest.raises(RuntimeError, match="unexpected controller"):
            await s.test_reference()
        assert s.last_pass is None

    asyncio.run(run())


@pytest.mark.parametrize("controller_fault", [False, True])
def test_snapshot_cli_distinguishes_candidate_errors_from_controller_faults(
    tmp_path, controller_fault
):
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps({"files": []} if controller_fault else {"files": [{}]}))
    receipt = tmp_path if controller_fault else tmp_path / "receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            str(HERE / "reference_remote.py"),
            "snapshot-inputs",
            str(manifest),
            str(receipt),
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if controller_fault:
        assert result.returncode != 0
        assert "IsADirectoryError" in result.stderr
    else:
        assert result.returncode == 0
        assert "local_path and source" in json.loads(result.stdout)["input_validation_error"]
        assert not receipt.exists()


@pytest.mark.parametrize(
    "original,changed",
    [
        ("result = 1\n", "import fractions\nresult = 1\n"),
        ("import json\nresult = 1\n", "result = 1\n"),
        ("import json\nresult = 1\n", "import json as renamed\nresult = 1\n"),
        ("from pathlib import Path\nresult = 1\n", "from pathlib import PurePath\nresult = 1\n"),
    ],
)
def test_source_import_repairs_are_refused_before_execution(tmp_path, original, changed):
    async def run():
        remote = FakeRemote()
        s = SetupSession(
            prepared=replace(prepared(), baseline=original),
            remote=remote,
            root=tmp_path,
            setup_seconds=60,
            reference_seconds=10,
            max_tests=1,
        )
        await s.initialize()
        remote.files["/work/setup/analysis.py"] = changed.encode()
        result = json.loads(await s.test_reference())
        assert result["status"] == "candidate_invalid"
        assert "Analysis imports changed" in result["error"]
        assert s.last_pass is None
        assert not any(
            label.startswith(("setup-", "reference-", "reset-env-")) for label, *_ in remote.events
        )

    asyncio.run(run())


def test_path_adaptation_with_original_imports_is_admitted(tmp_path):
    from reference_setup import inspect_candidate

    original = "from pathlib import Path\nresult = Path('remote-input.csv')\n"
    changed = (
        "# Offline path adaptation\nfrom pathlib import Path\nresult = Path('/inputs/data.csv')\n"
    )
    for name, data in FakeRemote().files.items():
        (tmp_path / Path(name).name).write_bytes(data)
    (tmp_path / "analysis.py").write_text(changed)
    _, script, _ = inspect_candidate(tmp_path, replace(prepared(), baseline=original))
    assert "/inputs/data.csv" in script


def successful_outcome(**changes):
    return SetupOutcome(
        disposition="tested",
        explanation="fixture",
        source_adaptations=[],
        unresolved_assumptions=[],
        **changes,
    )


def test_real_preparation_is_consumed_without_regeneration(tmp_path):
    source = HERE / "preparation-runs/010"
    p = PreparedReference.load(source)
    assert p.exports == (source / "exports.py").read_text()
    copy = tmp_path / "prepared"
    shutil.copytree(source, copy)
    (copy / "exports.py").write_text('print("changed")')
    with pytest.raises(ValueError, match="export identity"):
        PreparedReference.load(copy)


def test_pending_budgets_refuse_before_any_execution():
    with pytest.raises(ValueError, match="Explicit agreed max_tests"):
        check_config(json.loads((HERE / "reference-setup.json").read_text()) | {"max_tests": None})


def test_offline_test_uses_frozen_exports_and_records_original_candidate(tmp_path):
    async def exercise():
        s = session(tmp_path)
        await s.initialize()
        s.remote.files["/work/frozen/exports.py"] = b"malicious modified export"
        result = json.loads(await s.test_reference())
        assert result["status"] == "reference_executed"
        assert s.remote.files["/work/reference.py"] == b"result = 1\n\n\nprint(result)\n"
        assert not s.remote.blocked
        assert (tmp_path / "trials/1/outputs/result.txt").read_bytes() == b"1\n"
        await s.validate_outcome(successful_outcome())
        commands = list(s.remote.events)
        assert "exhausted" in await s.test_reference()
        assert s.remote.events == commands

    asyncio.run(exercise())


def test_worker_cannot_claim_success_without_test_or_after_changing_files(tmp_path):
    async def exercise():
        s = session(tmp_path)
        with pytest.raises(ValueError, match="successful controller test"):
            await s.validate_outcome(successful_outcome())
        await s.initialize()
        await s.test_reference()
        s.remote.files["/work/setup/stage-inputs.sh"] = b"changed recipe"
        with pytest.raises(ValueError, match="changed after"):
            await s.validate_outcome(successful_outcome())

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["setup_failure", "missing_output", "mutated_input"])
def test_failure_preserves_evidence_and_cannot_be_submitted_as_success(tmp_path, kind):
    async def exercise():
        s = session(tmp_path, FakeRemote(**{kind: True}))
        await s.initialize()
        if kind == "mutated_input":
            with pytest.raises(RuntimeError, match="checksum"):
                await s.test_reference()
        else:
            assert json.loads(await s.test_reference())["status"] in {
                "setup_failed",
                "reference_failed",
            }
        assert s.last_pass is None
        assert (tmp_path / "trials/1/result.json").exists()
        with pytest.raises(ValueError, match="successful controller test"):
            await s.validate_outcome(successful_outcome())
        if kind == "setup_failure":
            assert not any(e[0].startswith("reference-") for e in s.remote.events)

    asyncio.run(exercise())


def test_source_adaptation_is_preserved_and_requires_explanation(tmp_path):
    async def exercise():
        s = session(tmp_path)
        await s.initialize()
        s.remote.files["/work/setup/analysis.py"] = b"# path adaptation fixture\nresult = 1\n"
        await s.test_reference()
        assert "path adaptation" in (tmp_path / "trials/1/source.diff").read_text()
        with pytest.raises(ValueError, match="Explain source adaptations"):
            await s.validate_outcome(successful_outcome())

    asyncio.run(exercise())


def test_input_receipts_hash_actual_bytes_and_detect_changes(tmp_path):
    data = tmp_path / "input.txt"
    data.write_text("observed fixture")
    manifest = tmp_path / "inputs.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {"local_path": str(data), "source": "fixture://original", "sha256": "untrusted"}
                ]
            }
        )
    )
    receipt = tmp_path / "receipt.json"
    snapshot_inputs(manifest, receipt, roots=(tmp_path,))
    assert verify_staging(receipt, roots=(tmp_path,))["files"] == 1
    data.write_text("changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_staging(receipt, roots=(tmp_path,))


def test_upstream_worker_uses_extra_test_tool_and_validates_submission(tmp_path):
    async def exercise():
        s = session(tmp_path / "setup")
        await s.initialize()
        calls = []
        answers = [
            response("test_reference", {}, 1),
            response("submit_artifact", successful_outcome().model_dump(), 2),
        ]

        async def complete(payload):
            calls.append(payload)
            assert payload["chat_template_kwargs"] == {"reasoning_effort": "medium"}
            assert "max_tokens" not in payload
            assert "test_reference" in [t["function"]["name"] for t in calls[0]["tools"]]
            return answers[len(calls) - 1]

        ledger = RequestLedger(tmp_path / "requests.sqlite", {"setup": Allowance(None, None)})
        result = await stage(
            schema=SetupOutcome,
            name="setup",
            prompt_name="notebook-reference-setup",
            context={"paths": {}},
            root=tmp_path / "worker",
            ledger=ledger,
            budget=AuthorBudget(
                RunBudget(BudgetLedger(tmp_path / "cost.sqlite", limit_usd="1"), "setup", "1"),
                tmp_path / "charges",
                "setup",
            ),
            complete=complete,
            deadline=time.time() + 60,
            limits=ChatLimits(
                max_output_tokens=None,
                max_input_bytes=None,
                max_response_bytes=None,
                tool_output_chars=None,
                reasoning_effort="medium",
            ),
            max_requests=None,
            validate=s.validate_outcome,
            recover_output_limit=False,
            shell=s.shell,
            extra_tools=[TEST_TOOL],
            extra_handlers={"test_reference": s.test_reference},
        )
        assert result.disposition == "tested"
        assert len(calls) == 2
        assert s.tests == 1
        assert (tmp_path / "worker/artifact-stage/trace/1/response.json").exists()

    asyncio.run(exercise())


def test_uncertain_remote_command_closes_tools_instead_of_retrying(tmp_path):
    from types import SimpleNamespace

    from run_reference_setup import Remote

    calls = []

    class Worker:
        def upload(self, *args):
            pass

        def exec(self, *args, **kwargs):
            calls.append(args)
            raise TimeoutError("lost provider response")

    async def exercise():
        remote = Remote(Worker(), SimpleNamespace(), tmp_path, time.time() + 100, 1)
        with pytest.raises(TimeoutError):
            await remote.command(["true"], 10, "uncertain")
        with pytest.raises(RuntimeError, match="uncertain"):
            await remote.network(False)
        with pytest.raises(RuntimeError, match="uncertain"):
            await remote.command(["true"], 10, "duplicate")
        assert len(calls) == 1
        evidence = json.loads((tmp_path / "operations/0001/operation.json").read_text())
        assert evidence["state"] == "uncertain"

    asyncio.run(exercise())


def test_failed_offline_policy_prevents_analysis(tmp_path):
    class NoOffline(FakeRemote):
        async def network(self, blocked):
            if blocked:
                raise RuntimeError("Offline policy failed")
            await super().network(blocked)

    async def exercise():
        s = session(tmp_path, NoOffline())
        await s.initialize()
        with pytest.raises(RuntimeError, match="Offline policy"):
            await s.test_reference()
        assert not any(e[0].startswith("reference-") for e in s.remote.events)
        assert s.last_pass is None

    asyncio.run(exercise())


@pytest.mark.parametrize("transport", ["blocking", "async_session"])
@pytest.mark.parametrize("export_failure", [False, True])
@pytest.mark.parametrize("setup_exhausted", [False, True])
def test_run_failure_exports_evidence_then_cleans_owned_sandbox(
    tmp_path, monkeypatch, export_failure, setup_exhausted, transport
):
    from types import SimpleNamespace

    import iris_bootstrap
    import run_reference_setup as runner

    events = []
    fixture = replace(prepared(), baseline="result = 1\noriginal_measurement(result)\n")
    fixture.context.update(
        limits={
            "gpu": False,
            "reference_seconds": 600,
            "base_image": "fixture",
            "task_cpus": 4,
            "task_memory_gib": 8,
            "task_disk_gib": 10,
        },
        source={},
        conversion={},
    )
    monkeypatch.setattr(runner.PreparedReference, "load", lambda p: fixture)
    sandbox = SimpleNamespace(
        id="owned-fixture", cpu=4, memory=8, disk=10, refresh_data=lambda **kw: None
    )
    provider = SimpleNamespace(create=lambda *a, **kw: sandbox)

    class Worker:
        def exec(self, *args, **kwargs):
            return SimpleNamespace(checked=lambda msg: None)

    monkeypatch.setattr(runner, "DaytonaWorker", lambda *a: Worker())

    class AsyncClient:
        async def get(self, identity, **kwargs):
            events.append("client-get")
            assert identity == sandbox.id
            return SimpleNamespace(id=identity, process="fixture-async-process")

        async def close(self):
            events.append("client-close")

    import daytona_session

    monkeypatch.setattr(daytona_session, "AsyncDaytona", AsyncClient)

    def remote(*args, **kwargs):
        assert kwargs == (
            {"session_process": "fixture-async-process"} if transport == "async_session" else {}
        )
        return FakeRemote()

    monkeypatch.setattr(runner, "Remote", remote)

    async def failed_stage(**kwargs):
        original = kwargs["context"]["source_operations"]
        assert original["source_sha256"] == hashlib.sha256(fixture.baseline.encode()).hexdigest()
        assert [call["source"] for call in original["operations"]] == [
            "original_measurement(result)"
        ]
        if setup_exhausted:
            session = kwargs["validate"].__self__
            session.setup_remaining = -30.18
            assert session.tests == 0
            return successful_outcome().model_copy(update={"disposition": "blocked"})
        raise RuntimeError("fixture stage failure")

    monkeypatch.setattr(runner, "stage", failed_stage)

    def export(*args, **kwargs):
        events.append("export")
        if export_failure:
            raise RuntimeError("fixture export failure")

    monkeypatch.setattr(iris_bootstrap, "export_on_host", export)
    monkeypatch.setattr(
        runner, "cleanup", lambda owner, client: events.append("cleanup") or {"passed": True}
    )
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "s3://fixture")
    config = json.loads((HERE / "reference-setup.json").read_text()) | {
        "max_requests": None,
        "max_tests": 1,
        "command_transport": transport,
    }
    error = runner.SetupBudgetExceeded if setup_exhausted and not export_failure else RuntimeError
    message = (
        "before any controlled reference dispatch"
        if setup_exhausted and not export_failure
        else "fixture (stage|export) failure"
    )
    with pytest.raises(error, match=message):
        asyncio.run(
            runner.run(
                config,
                root=tmp_path / "run",
                deadline=time.time() + 1000,
                endpoint="unused",
                credential="unused",
                provider=provider,
                complete=lambda p: None,
            )
        )
    assert events == (
        ["client-get", "client-close", "export", "cleanup"]
        if transport == "async_session"
        else ["export", "cleanup"]
    )
    result = json.loads((tmp_path / "run/result.json").read_text())
    assert result["status"] == "incomplete" and result["cleanup_verified"]
    assert result["construction_run"] is False and result["solver_run"] is False
    if setup_exhausted:
        assert result["incomplete_reason"] == "setup_budget_exhausted_before_reference"
        assert result["error_type"] == "SetupBudgetExceeded"
        assert result["reference_tests"] == 0
        assert result["setup_seconds_remaining"] == -30.18
        assert json.loads((tmp_path / "run/outcome.json").read_text())["disposition"] == "blocked"
