"""Append independent challenges without editing the original probe programs."""

import json
import shlex
from typing import Literal

from grading_protocol import Probe, Probes, check_probes, parse_report
from pydantic import Field, model_validator
from reference_protocol import StrictModel
from repo2rlenv.execution.lifecycle import save_record


def unexercised_scientific_checks(candidate, controls):
    """Require an executed declared negative, not a nominal ID or missing-file case.

    This is a coverage guard, not proof that the mutation is scientifically wrong.
    Independent review must still establish that fact from the public contract.
    """
    covered = set()
    for control in controls:
        probe = control.get("probe") or {}
        execution = control.get("execution") or {}
        grader = execution.get("grader") or {}
        if (
            control.get("kind") != "probe"
            or probe.get("kind") != "wrong_solution"
            or execution.get("status") != "executed"
            or execution.get("probe_valid_execution") is not True
            or type(grader.get("exit_code")) is not int
            or grader["exit_code"] != 0
        ):
            continue
        try:
            report = parse_report(execution.get("report"), candidate)
        except ValueError:
            continue
        failed = {row["id"] for row in report["checks"] if row["passed"] is False}
        covered.update(set(probe.get("check_ids", [])) & failed)
    return sorted({c.id for c in candidate.checks if c.kind == "scientific"} - covered)


class ProbeSupplement(StrictModel):
    disposition: Literal["ready", "blocked"]
    probes: list[Probe]
    concerns: list[str]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def additions_only(self):
        if self.disposition == "blocked":
            if self.probes or not self.concerns:
                raise ValueError("A blocked supplement needs concerns and no new probes")
        elif not self.probes or any(p.kind != "wrong_solution" for p in self.probes):
            raise ValueError("A ready supplement requires only additional wrong-result probes")
        return self


def append_supplement(original, supplement, candidate, targets):
    """Preserve every original field; reject replacements and unrelated claims."""
    if supplement.disposition != "ready":
        raise ValueError("A blocked supplement cannot extend the suite")
    allowed = set(targets)
    if not allowed or allowed - {c.id for c in candidate.checks if c.kind == "scientific"}:
        raise ValueError("Supplement targets must be existing scientific checks")
    declared = set()
    for probe in supplement.probes:
        if not set(probe.check_ids) <= allowed:
            raise ValueError("Supplement claims a check outside its assigned coverage targets")
        declared.update(probe.check_ids)
    if declared != allowed:
        raise ValueError("Supplement does not cover every assigned scientific check")
    result = Probes(
        disposition="ready",
        probes=[*original.probes, *supplement.probes],
        concerns=[*original.concerns, *supplement.concerns],
    )
    check_probes(result, candidate)
    return result


def supplement_context(probe_context, original, targets):
    """An allowlist keeps grader, execution reports and raw inputs out of this role."""
    return {
        key: probe_context[key]
        for key in (
            "artifact_interface",
            "public_instruction",
            "checks",
            "paths",
            "output_paths",
            "reference_seconds",
            "verifier_seconds",
        )
    } | {"original_probes": original.model_dump(), "coverage_targets": list(targets)}


async def prepare_supplement(
    *, session, call, probe_context, original, candidate, controls, targets, hide_inputs, root
):
    """One separate GLM role inside the existing single quality-repair route.

    Preflight exposes only execution/mutation evidence; grader results are never
    sent to this role. All original and added controls run in the existing repair.
    """
    if list(targets) != unexercised_scientific_checks(candidate, controls):
        raise ValueError("Supplement targets differ from the controller's executed coverage")
    save_record(
        root / "probe-coverage-baseline.json",
        {
            "candidate": candidate.model_dump(),
            "original_probes": original.model_dump(),
            "controls": controls,
            "targets": list(targets),
        },
    )
    cleared = await session.command(["rm", "-rf", "/case"], 30, "clear-grader-before-supplement")
    if cleared["exit_code"]:
        raise RuntimeError("Cannot isolate supplemental probe author from grader remnants")
    if hide_inputs:
        hidden = await session.command(
            ["chmod", "700", "/work/task-inputs"], 30, "hide-inputs-before-supplement"
        )
        if hidden["exit_code"]:
            raise RuntimeError("Cannot hide raw inputs from supplemental probe author")

    async def shell(command, timeout_sec=120):
        return await session.shell(command, timeout_sec, role="probe")

    # These paths must stay inaccessible even if permissions drifted after the
    # original probe stage. Reference results are intentionally available.
    paths = ["/work/grading-private", "/work/author"]
    if hide_inputs:
        paths.append("/work/task-inputs")
    code = (
        "from pathlib import Path\n"
        f"for name in {paths!r}:\n"
        " try:\n  list(Path(name).iterdir())\n"
        " except PermissionError:\n  continue\n"
        " raise RuntimeError('Private author material accessible')\n"
        "print('isolated')"
    )
    isolation = json.loads(await shell("/work/venv/bin/python -c " + shlex.quote(code), 15))
    if isolation.get("exit_code") != 0 or isolation.get("stdout", "").strip() != "isolated":
        raise RuntimeError("Supplemental probe-author isolation not established")

    async def validate(value):
        if value.disposition == "ready":
            append_supplement(original, value, candidate, targets)
            for probe in value.probes:
                await session.validate_probe_execution(probe)

    supplement = await call(
        ProbeSupplement,
        "probe-supplement",
        "notebook-grader-probe-supplement",
        supplement_context(probe_context, original, targets),
        validate,
        shell,
    )
    save_record(root / "probe-supplement.json", supplement.model_dump())
    # Restore only after a successful stage. On an uncertain failure the owning
    # lifecycle deletes the sandbox instead of dispatching another mutation.
    if hide_inputs:
        restored = await session.command(
            ["chmod", "555", "/work/task-inputs"], 30, "restore-inputs-after-supplement"
        )
        if restored["exit_code"]:
            raise RuntimeError("Cannot restore raw-input permissions after supplement")
    if supplement.disposition == "blocked":
        return None
    result = append_supplement(original, supplement, candidate, targets)
    save_record(root / "supplemented-probes.json", result.model_dump())
    return result
