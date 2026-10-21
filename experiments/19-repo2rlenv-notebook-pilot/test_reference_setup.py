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
from reference_setup import TEST_TOOL, PreparedReference, SetupOutcome, SetupSession
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
        }
        self.events = []
        self.blocked = False
        self.setup_failure = setup_failure
        self.missing_output = missing_output
        self.mutated_input = mutated_input

    async def upload(self, local, remote):
        self.files[remote] = local.read_bytes()

    async def download(self, remote, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(self.files[remote])

    async def command(self, argv, seconds, label, *, cwd="/work"):
        self.events.append((label, self.blocked, cwd))
        if label.startswith("reference-"):
            assert self.blocked
            assert cwd == "/work/run"
            self.files["/work/outputs/result.txt"] = b"1\n"
        if label.startswith("setup-"):
            self.files["/work/environment/uv.lock"] = b"version = 1\n"
            self.files["/work/environment/environment.txt"] = b""
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
        assert not any(label.startswith(("setup-", "reference-", "reset-env-")) for label, *_ in remote.events)

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
        s = SetupSession(prepared=prepared(), remote=remote, root=tmp_path,
                         setup_seconds=60, reference_seconds=10, max_tests=2)
        await s.initialize()
        result = json.loads(await s.test_reference())
        assert result["status"] == "candidate_invalid"
        assert "Missing declared" in result["error"]
        assert s.last_pass is None
        assert not any(label.startswith("reference-") for label, *_ in remote.events)
        # A corrected staging recipe can use the already-agreed second test.
        remote.invalid = False
        assert json.loads(await s.test_reference())["status"] == "reference_executed"
        assert s.last_pass["test"] == 2

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
def test_snapshot_cli_distinguishes_candidate_errors_from_controller_faults(tmp_path, controller_fault):
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps({"files": []} if controller_fault else {"files": [{}]}))
    receipt = tmp_path if controller_fault else tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(HERE / "reference_remote.py"), "snapshot-inputs", str(manifest), str(receipt)],
        capture_output=True, text=True, timeout=5,
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


@pytest.mark.parametrize("export_failure", [False, True])
def test_run_failure_exports_evidence_then_cleans_owned_sandbox(
    tmp_path, monkeypatch, export_failure
):
    from types import SimpleNamespace

    import iris_bootstrap
    import run_reference_setup as runner

    events = []
    fixture = prepared()
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
    monkeypatch.setattr(runner, "Remote", lambda *a: FakeRemote())

    async def failed_stage(**kwargs):
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
    }
    with pytest.raises(RuntimeError, match="fixture (stage|export) failure"):
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
    assert events == ["export", "cleanup"]
    result = json.loads((tmp_path / "run/result.json").read_text())
    assert result["status"] == "incomplete" and result["cleanup_verified"]
    assert result["construction_run"] is False and result["solver_run"] is False
