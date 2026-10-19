"""Pre-Harbor artifact grading through Tasksmith workers and the Daytona controller."""

import json
import shlex
import time
from pathlib import Path

import httpx
from design_stage import completion_transport
from grading_protocol import (
    AlternativeSolution,
    Grader,
    Probes,
    Review,
    check_coverage,
    check_probes,
    parse_report,
)
from openai import AsyncOpenAI
from reference_environment import setup_script
from reference_replay import sha256
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger

HERE = Path(__file__).parent

ISOLATION_PROBE = """import os
from pathlib import Path
assert os.getuid() != 0
p = next(p for p in Path('/work/reference').rglob('*') if p.is_file())
try:
    p.open('ab')
    raise AssertionError('reference writable')
except PermissionError:
    pass
try:
    list(Path('/work/grading-private').iterdir())
    raise AssertionError('private readable')
except PermissionError:
    pass
print('isolated')
"""


class GradingSession:
    def __init__(self, *, remote, snapshot, root, config):
        self.remote, self.snapshot, self.root, self.config = remote, snapshot, root, config
        self.paths = [p["path"] for p in snapshot["outputs"]]
        self.case_number = 0
        self.candidate_number = 0
        self.last_candidate = None
        self.last_controls = []
        self.frozen_probes = None
        self.frozen_checks = None
        self.alternative_validated = False
        self.root.mkdir(parents=True, exist_ok=False)

    async def command(self, argv, seconds, label):
        return await self.remote.command(argv, seconds, label)

    async def helper(self, args, seconds, label):
        # Always restore controller code; workers never author or edit this helper.
        await self.remote.upload(HERE / "grading_remote.py", "/work/grading_remote.py")
        reply = await self.command(["python", "/work/grading_remote.py", *args], seconds, label)
        if reply["exit_code"]:
            raise RuntimeError("Grading controller failed: " + reply["log"])
        value = json.loads(reply["log"]) if reply["log"].strip() else None
        if args[0] != "case" and isinstance(value, dict) and value.get("status") == "incomplete":
            raise RuntimeError("Controller operation failed: " + json.dumps(value))
        return value

    async def initialize(self):
        source = self.snapshot["directory"]
        setup = self.root / "setup.sh"
        setup.write_text(
            setup_script(self.snapshot["system_packages"], verify_inputs=False, locked=True)
        )
        staging = self.root / "no-input-staging.sh"
        staging.write_text(
            (source / "candidate/stage-inputs.sh").read_text()
            if self.config.get("materialize_task")
            else "#!/bin/sh\nexit 0\n"
        )
        reply = await self.command(
            ["mkdir", "-p", "/work/environment", "/work/grading-private/oracle", "/work/reference"],
            30,
            "grading-initialize",
        )
        if reply["exit_code"]:
            raise RuntimeError("Cannot initialize grading workspace")
        await self.helper(["initialize"], 30, "grading-users")
        locked_logs = await self.command(["chmod", "700", "/work/logs"], 30, "grading-private-logs")
        if locked_logs["exit_code"]:
            raise RuntimeError("Cannot isolate controller logs")
        for local, target in [
            (source / "candidate/pyproject.toml", "/work/environment/pyproject.toml"),
            (source / "trial/uv.lock", "/work/environment/uv.lock"),
            (setup, "/work/setup.sh"),
            (staging, "/work/stage-inputs.sh"),
        ]:
            await self.remote.upload(local, target)
        await self.remote.network(False)
        built = await self.command(
            ["sh", "-eu", "/work/setup.sh"], self.config["setup_seconds"], "grading-environment"
        )
        save_record(self.root / "setup-result.json", built)
        if built["exit_code"]:
            raise RuntimeError("Locked grading environment setup failed")
        for name in ("uv.lock", "environment.txt"):
            await self.remote.download("/work/environment/" + name, self.root / name)
            if sha256(self.root / name) != self.snapshot["hashes"]["trial/" + name]:
                raise RuntimeError("Grading environment differs from the reference")
        root = Path(
            self.snapshot.get(
                "restored_outputs_root",
                "/work/grading-inputs/reference-replay/replay/trials/1/outputs",
            )
        )
        for item in self.snapshot["outputs"]:
            original = root / item["path"]
            if sha256(original) != item["sha256"] or original.stat().st_size != item["bytes"]:
                raise ValueError("Restored reference bytes changed")
            for parent in ("/work/grading-private/oracle", "/work/reference"):
                directory = str(Path(parent) / Path(item["path"]).parent)
                made = await self.command(
                    ["mkdir", "-p", directory],
                    30,
                    "grading-reference-parent-" + str(time.time_ns()),
                )
                if made["exit_code"]:
                    raise RuntimeError("Cannot create reference artifact directory")
                await self.remote.upload(original, parent + "/" + item["path"])
        if "materialization" in self.snapshot:
            derived = self.snapshot["materialization"]["execution"]
            for kind, remote_root in (
                ("inputs", "/work/task-inputs"),
                ("oracle_outputs", "/work/grading-private/recomputed"),
            ):
                for item in derived[kind]:
                    local = Path("/work/grading-inputs/grading/materialized") / kind / item["path"]
                    if local.stat().st_size != item["bytes"] or sha256(local) != item["sha256"]:
                        raise ValueError("Derived input/oracle archive identity mismatch")
                    made = await self.command(
                        ["mkdir", "-p", str(Path(remote_root, item["path"]).parent)],
                        30,
                        "derived-parent-" + str(time.time_ns()),
                    )
                    if made["exit_code"]:
                        raise RuntimeError("Cannot stage derived artifact")
                    await self.remote.upload(local, remote_root + "/" + item["path"])
            copied = await self.command(
                [
                    "sh",
                    "-eu",
                    "-c",
                    "cp -a /work/grading-private/recomputed /work/recomputed; chmod -R a+rX,a-w /work/recomputed",
                ],
                30,
                "stage-recomputed-comparison",
            )
            if copied["exit_code"]:
                raise RuntimeError("Cannot expose recomputation evidence")
            sealed = await self.command(
                ["chmod", "-R", "a-w", "/work/task-inputs"], 30, "seal-task-inputs"
            )
            if sealed["exit_code"]:
                raise RuntimeError("Cannot freeze derived inputs")
        expected = self.root / "expected.json"
        save_record(expected, {p["path"]: p["sha256"] for p in self.snapshot["outputs"]})
        await self.remote.upload(expected, "/work/grading-private/expected.json")
        locked = await self.command(
            [
                "sh",
                "-eu",
                "-c",
                "chmod -R a-w /work/reference; chmod -R go-rwx /work/grading-private",
            ],
            30,
            "grading-readonly-reference",
        )
        if locked["exit_code"]:
            raise RuntimeError("Cannot freeze grading reference permissions")
        if self.config.get("materialize_task"):
            expected_inputs = source / "trial/inputs-before.json"
            await self.remote.upload(expected_inputs, "/work/original-inputs.json")
            await self.remote.helper(
                ["verify-staging", "/work/original-inputs.json"], "materialization-original-inputs"
            )
        await self.remote.network(True)
        # Verify actual filesystem/user boundaries before any generated code runs.
        for role in ("author", "probe"):
            checked = await self.shell(
                "/work/venv/bin/python -c " + shlex.quote(ISOLATION_PROBE), 30, role=role
            )
            value = json.loads(checked)
            if value["exit_code"] or value["stdout"].strip() != "isolated":
                raise RuntimeError("Worker filesystem isolation not established: " + checked)
        save_record(
            self.root / "isolation.json",
            {"unprivileged_workers": True, "reference_readonly": True, "controller_private": True},
        )

    async def shell(self, command, timeout_sec=120, *, role="author"):
        if type(timeout_sec) is not int or not 1 <= timeout_sec <= self.config["reference_seconds"]:
            raise ValueError("Shell timeout must fit the agreed single-computation allowance")
        reply = await self.helper(
            ["shell", role, command, str(timeout_sec)],
            timeout_sec + 10,
            "grading-shell-" + str(time.time_ns()),
        )
        return json.dumps(reply)

    async def case(self, candidate, *, kind, omit=None, probe=None):
        self.case_number += 1
        folder = self.root / "controls" / f"{self.case_number:04d}"
        folder.mkdir(parents=True)
        request = {"kind": kind, "seconds": self.config["verifier_seconds"]}
        if omit:
            request["omit"] = omit
        if probe:
            request["script"] = probe.script
        save_record(folder / "request.json", request)
        await self.remote.upload(folder / "request.json", "/work/grading-private/request.json")
        reply = await self.helper(
            ["case"],
            self.config["verifier_seconds"] * (2 if probe else 1) + 10,
            "grading-control-" + str(self.case_number),
        )
        record = {
            "candidate_sha256": sha256(self.last_candidate / "candidate.json"),
            "kind": kind,
            "omitted": omit,
            "probe": probe.model_dump() if probe else None,
            "execution": reply,
            "passed_control": False,
        }
        try:
            if (
                reply["status"] != "executed"
                or reply["grader"]["exit_code"] != 0
                or "report" not in reply
            ):
                record["problem"] = "Verifier or probe did not complete successfully"
                return record
            report = parse_report(reply["report"], candidate)
            failed = {r["id"] for r in report["checks"] if not r["passed"]}
            expected_pass = kind in {"reference", "recomputed", "alternative"} or (
                probe and probe.kind == "valid_alternative"
            )
            record["passed_control"] = report["passed"] == bool(expected_pass)
            if probe and probe.kind == "wrong_solution":
                record["passed_control"] &= set(probe.check_ids) <= failed
            return record
        except ValueError as error:
            record["problem"] = str(error)
            return record
        finally:
            save_record(folder / "result.json", record)

    async def validate_candidate(self, candidate):
        if candidate.disposition == "blocked":
            return
        check_coverage(candidate, self.paths)
        if self.frozen_checks is not None and candidate.checks != self.frozen_checks:
            raise ValueError(
                "Repair cannot change the frozen check inventory; report a blocker if coverage must change"
            )
        self.candidate_number += 1
        folder = self.root / "candidates" / str(self.candidate_number)
        folder.mkdir(parents=True)
        save_record(folder / "candidate.json", candidate.model_dump())
        (folder / "instruction.md").write_text(candidate.instruction + "\n")
        (folder / "grade.py").write_text(candidate.grader_code + "\n")
        self.last_candidate = folder
        await self.remote.upload(folder / "grade.py", "/work/grading-private/grade.py")
        controls = [
            await self.case(candidate, kind="reference"),
            await self.case(candidate, kind="empty"),
        ]
        if "materialization" in self.snapshot:
            controls.append(await self.case(candidate, kind="recomputed"))
        if self.alternative_validated:
            controls.append(await self.case(candidate, kind="alternative"))
        for name in self.paths:
            controls.append(await self.case(candidate, kind="missing", omit=name))
        if self.frozen_probes:
            for probe in self.frozen_probes.probes:
                controls.append(await self.case(candidate, kind="probe", probe=probe))
        save_record(folder / "controls.json", controls)
        self.last_controls = controls
        failures = [r for r in controls if not r["passed_control"]]
        if failures:
            raise ValueError("Executable control failures: " + json.dumps(failures))


async def run_grading(
    *, remote, snapshot, root, config, endpoint, credential, deadline, complete=None
):
    session = GradingSession(remote=remote, snapshot=snapshot, root=root / "grading", config=config)
    await session.initialize()
    reference = snapshot["directory"]
    spec = HERE / config["specification_directory"]
    # Each stage receives an explicit, reproducible input object; no hidden task edits.
    context = {
        "specification": json.loads((spec / "specification.json").read_text()),
        "operator_handoff": (spec / "README.md").read_text(),
        "source_evidence": {
            name: (reference / name).read_text()
            for name in (
                "inputs/original.py",
                "inputs/exports.py",
                "inputs/plan.json",
                "trial/source.diff",
                "candidate/pyproject.toml",
                "trial/environment.txt",
            )
        },
        "reference_observations": json.loads((reference / "output-audit.json").read_text()),
        "repeatability": json.loads(
            (HERE / config["replay_directory"] / "result.json").read_text()
        ),
        "policy": json.loads(
            (HERE / config.get("policy_file", "specification-reference-policy.json")).read_text()
        ),
        "paths": {"reference_outputs": "/work/reference", "working_directory": "/work/author"},
        "verifier_seconds": config["verifier_seconds"],
        "reference_seconds": config["reference_seconds"],
    }
    if "materialization" in snapshot:
        context["materialization"] = snapshot["materialization"]
        # The executed task supersedes speculative specification-stage plans.
        # Actual replay and independent-execution records supply validation facts.
        context["specification"] = {
            "task_brief": snapshot["materialization"]["candidate"]["instruction"],
        }
        context.pop("operator_handoff")
        context["paths"]["task_inputs"] = "/work/task-inputs"
        context["paths"]["recomputed_outputs"] = "/work/recomputed"
    if config.get("materialize_task"):
        from task_materialization import run_materialization

        return await run_materialization(
            session=session,
            context=context,
            root=root,
            config=config,
            endpoint=endpoint,
            credential=credential,
            deadline=deadline,
            complete=complete,
        )
    resumed = None
    if config.get("resume_grading_directory"):
        from grading_resume import load_resume

        if "materialization" not in snapshot:
            raise ValueError("Grading resume requires materialized task inputs")
        resumed = load_resume(HERE / config["resume_grading_directory"], context)
        save_record(
            root / "resume.json",
            {
                "source": config["resume_grading_directory"],
                "reexecute_independent": True,
                "revalidate_grader_controls": True,
                "prior_acceptance_reused": False,
            },
        )
    saved_probes = None
    if config.get("resume_probes_directory"):
        from grading_resume import load_saved_probes

        if not resumed:
            raise ValueError("Probe recovery requires scientific-context-verified grader recovery")
        saved_probes = load_saved_probes(HERE / config["resume_probes_directory"], resumed[1])
        save_record(
            root / "probe-resume.json",
            {
                "source": config["resume_probes_directory"],
                "partial_snapshot": True,
                "reexecute_all_probes": True,
                "prior_acceptance_reused": False,
            },
        )
    scopes = ("independent", "grader", "probes", "review", "repair", "review-repair")
    ledger = RequestLedger(root / "requests.sqlite", {s: Allowance(None, None) for s in scopes})
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "grading", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort="medium",
        request_timeout_sec=config["request_timeout_seconds"],
    )
    client = None
    if complete is None:
        client = AsyncOpenAI(
            base_url=endpoint,
            api_key=credential,
            max_retries=0,
            timeout=limits.request_timeout_sec,
            http_client=httpx.AsyncClient(follow_redirects=False),
        )
        complete = completion_transport(client)

    async def call(schema, name, prompt, inputs, validate=None, shell=None):
        return await stage(
            schema=schema,
            name=name,
            prompt_name=prompt,
            context=inputs,
            root=root / name,
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", name),
            complete=complete,
            deadline=deadline,
            limits=limits,
            max_requests=None,
            validate=validate,
            shell=shell,
            shell_timeout_sec=config["reference_seconds"],
            recover_output_limit=False,
        )

    try:
        if "materialization" in snapshot:

            async def independent_shell(command, timeout_sec=120):
                return await session.shell(command, timeout_sec, role="probe")

            async def validate_independent(value):
                if value.disposition == "blocked":
                    return
                folder = root / "independent-executions" / str(time.time_ns())
                folder.mkdir(parents=True)
                save_record(
                    folder / "request.json",
                    {
                        "code": value.code,
                        "output_paths": session.paths,
                        "seconds": config["reference_seconds"],
                    },
                )
                await session.remote.upload(
                    folder / "request.json", "/work/grading-private/alternative-request.json"
                )
                await session.remote.upload(
                    HERE / "alternative_remote.py", "/work/alternative_remote.py"
                )
                await session.remote.upload(HERE / "grading_remote.py", "/work/grading_remote.py")
                reply = await session.command(
                    ["python", "/work/alternative_remote.py"],
                    config["reference_seconds"] + 30,
                    "independent-" + folder.name,
                )
                result = {"controller": reply}
                if reply["exit_code"] == 0:
                    result["execution"] = json.loads(reply["log"])
                save_record(folder / "result.json", result)
                if (
                    reply["exit_code"]
                    or result["execution"]["status"] != "executed_without_answer_access"
                ):
                    raise ValueError("Independent execution failed: " + json.dumps(result))
                for item in result["execution"]["outputs"]:
                    path = root / "independent-outputs" / item["path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    await session.remote.download(
                        "/work/grading-private/alternative/" + item["path"], path
                    )
                    if sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
                        raise ValueError("Independent output download identity mismatch")
                save_record(root / "independent-result.json", result["execution"])
                session.alternative_validated = True

            hidden = await session.command(
                ["chmod", "700", "/work/reference", "/work/recomputed"],
                30,
                "hide-validation-answers",
            )
            if hidden["exit_code"]:
                raise RuntimeError("Cannot isolate independent solution from answers")
            try:
                isolation = await independent_shell(
                    "/work/venv/bin/python -c "
                    + shlex.quote(
                        "from pathlib import Path\n"
                        "for p in ['/work/reference','/work/recomputed','/work/grading-private','/work/author']:\n"
                        " try:\n  list(Path(p).iterdir())\n"
                        " except PermissionError:\n  continue\n"
                        " raise RuntimeError('Private answers accessible')\n"
                        "print('isolated')"
                    ),
                    15,
                )
                if json.loads(isolation)["exit_code"]:
                    raise RuntimeError("Independent solution isolation check failed")
                if resumed:
                    independent = resumed[0]
                    await validate_independent(independent)
                else:
                    independent = await call(
                        AlternativeSolution,
                        "independent",
                        "notebook-task-independent-solution",
                        {
                            "public_instruction": context["specification"]["task_brief"],
                            "input_paths": snapshot["materialization"]["candidate"]["input_paths"],
                            "output_paths": session.paths,
                            "environment": context["source_evidence"]["trial/environment.txt"],
                            "paths": {
                                "inputs": "/work/task-inputs",
                                "working_directory": "/work/probe",
                            },
                            "reference_seconds": config["reference_seconds"],
                            "policy": context["policy"],
                        },
                        validate_independent,
                        independent_shell,
                    )
                save_record(root / "independent-solution.json", independent.model_dump())
            finally:
                restored = await session.command(
                    ["chmod", "555", "/work/reference", "/work/recomputed"],
                    30,
                    "restore-author-reference-access",
                )
                if restored["exit_code"]:
                    raise RuntimeError("Cannot restore grading evidence access")
            if independent.disposition == "blocked":
                return {"status": "independent_solution_blocked"}
            exposed = await session.command(
                [
                    "sh",
                    "-eu",
                    "-c",
                    "cp -a /work/grading-private/alternative /work/alternative; chmod -R a+rX,a-w /work/alternative",
                ],
                30,
                "expose-independent-evidence",
            )
            if exposed["exit_code"]:
                raise RuntimeError("Cannot expose independent evidence for comparison")
            context["independent_solution"] = independent.model_dump()
            context["independent_execution"] = json.loads(
                (root / "independent-result.json").read_text()
            )
            context["paths"]["independent_outputs"] = "/work/alternative"
        if resumed:
            candidate = resumed[1]
            await session.validate_candidate(candidate)
        else:
            candidate = await call(
                Grader,
                "grader",
                "notebook-grader-author",
                context,
                session.validate_candidate,
                session.shell,
            )
        save_record(root / "candidate.json", candidate.model_dump())
        if candidate.disposition == "blocked":
            return {"status": "grader_blocked", "grader_construction_run": True}
        # Remove author test remnants before the separate probe worker gets a shell.
        cleared = await session.command(
            ["rm", "-rf", "/case"], 30, "clear-grader-before-probe-author"
        )
        if cleared["exit_code"]:
            raise RuntimeError("Cannot isolate independent probe author")
        # The independent solver used this same unprivileged work directory.
        # Its submitted code and outputs are already preserved by the controller.
        cleared = await session.command(
            ["find", "/work/probe", "-mindepth", "1", "-delete"],
            30,
            "clear-independent-workspace-before-probes",
        )
        if cleared["exit_code"]:
            raise RuntimeError("Cannot clear prior independent-solution working files")

        async def validate_probes(suite):
            if suite.disposition == "ready":
                check_probes(suite, candidate)

        async def probe_shell(command, timeout_sec=120):
            return await session.shell(command, timeout_sec, role="probe")

        probe_context = {
            "public_instruction": context["specification"]["task_brief"].rstrip()
            + "\n\n## Acceptance rules\n\n"
            + candidate.instruction,
            "checks": [c.model_dump() for c in candidate.checks],
            "paths": {"reference_outputs": "/work/reference", "working_directory": "/work/probe"},
            "output_paths": session.paths,
            "reference_seconds": config["reference_seconds"],
            "verifier_seconds": config["verifier_seconds"],
        }
        hide_inputs = "materialization" in snapshot
        if hide_inputs:
            reply = await session.command(
                ["chmod", "700", "/work/task-inputs"], 30, "hide-raw-inputs-from-probe-author"
            )
            if reply["exit_code"]:
                raise RuntimeError("Cannot isolate probe author from raw task inputs")
        try:
            if hide_inputs:
                isolated = await probe_shell(
                    "/work/venv/bin/python -c "
                    + shlex.quote(
                        "from pathlib import Path\n"
                        "try:\n list(Path('/work/task-inputs').iterdir())\n"
                        "except PermissionError:\n print('isolated')\n"
                        "else:\n raise RuntimeError('Raw task inputs accessible')\n"
                    ),
                    15,
                )
                checked = json.loads(isolated)
                if checked["exit_code"] or checked["stdout"].strip() != "isolated":
                    raise RuntimeError("Probe raw-input isolation check failed")
            if saved_probes is not None:
                probes = saved_probes
                await validate_probes(probes)
            else:
                probes = await call(
                    Probes,
                    "probes",
                    "notebook-grader-probes",
                    probe_context,
                    validate_probes,
                    probe_shell,
                )
        finally:
            if hide_inputs:
                reply = await session.command(
                    ["chmod", "555", "/work/task-inputs"], 30, "restore-raw-inputs-after-probes"
                )
                if reply["exit_code"]:
                    raise RuntimeError("Cannot restore raw-input permissions")
        save_record(root / "probes.json", probes.model_dump())
        if probes.disposition == "blocked":
            return {"status": "probe_author_blocked", "grader_construction_run": True}
        session.frozen_probes, session.frozen_checks = probes, candidate.checks
        for probe in probes.probes:
            session.last_controls.append(await session.case(candidate, kind="probe", probe=probe))

        async def review(name):
            async def validate_review(value):
                if value.decision == "accept_for_packaging" and (
                    value.issues or not all(c["passed_control"] for c in session.last_controls)
                ):
                    raise ValueError(
                        "Acceptance requires all executed controls to pass and no unresolved issues"
                    )

            return await call(
                Review,
                name,
                "notebook-grader-review",
                {
                    **context,
                    "candidate": candidate.model_dump(),
                    "probes": probes.model_dump(),
                    "controls": session.last_controls,
                },
                validate_review,
            )

        assessment = await review("review")
        save_record(root / "review.json", assessment.model_dump())
        if assessment.decision == "revise":
            candidate = await call(
                Grader,
                "repair",
                "notebook-grader-author",
                {
                    **context,
                    "prior_candidate": candidate.model_dump(),
                    "review": assessment.model_dump(),
                    "frozen_probes": probes.model_dump(),
                    "controls": session.last_controls,
                },
                session.validate_candidate,
                session.shell,
            )
            save_record(root / "repaired-candidate.json", candidate.model_dump())
            if candidate.disposition == "blocked":
                return {"status": "repair_blocked", "grader_construction_run": True}
            assessment = await review("review-repair")
            save_record(root / "review-repair.json", assessment.model_dump())
        save_record(root / "final-controls.json", session.last_controls)
        save_record(root / "final-candidate.json", candidate.model_dump())
        (root / "instruction.md").write_text(
            context["specification"]["task_brief"].rstrip()
            + "\n\n## Acceptance rules\n\n"
            + candidate.instruction
            + "\n"
        )
        (root / "grade.py").write_text(candidate.grader_code + "\n")
        return {
            "status": "grader_candidate_validated"
            if assessment.decision == "accept_for_packaging"
            else "grader_requires_further_work",
            "grader_construction_run": True,
            "control_cases": session.case_number,
            "final_controls_passed": all(c["passed_control"] for c in session.last_controls),
            "review_decision": assessment.decision,
            "harbor_packaging_validated": False,
            "software_portability_validated": False,
        }
    finally:
        if client:
            await client.close()
