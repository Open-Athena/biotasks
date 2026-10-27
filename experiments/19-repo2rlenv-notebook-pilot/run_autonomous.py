"""One frozen notebook seed through existing workers, controls and native Harbor.

No operator handoffs or automatic source-code changes. Model workers own all
scientific artifacts. Exceptions are infrastructure/incomplete outcomes, never
successful notebook rejections. Run on the reserved Iris host, not the shared VM.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from campaign_budget import (
    SANDBOX_STAGES,
    STAGE_RESERVATION_USD,
    require_full_pipeline_budget,
)
from model_profile import native_effort

HERE = Path(__file__).parent


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(root):
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Evidence must not contain symbolic links")
        if path.is_file():
            result.append(
                dict(
                    path=path.relative_to(root).as_posix(),
                    bytes=path.stat().st_size,
                    sha256=digest(path),
                )
            )
    return result


def copy_verified(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if digest(source) != digest(target):
        raise ValueError("Handoff copy identity mismatch")


class Rejected(Exception):
    def __init__(self, stage, reason, evidence):
        self.stage, self.reason, self.evidence = stage, reason, evidence
        super().__init__(reason)


def require_worker(path, expected, *, stage, field="disposition"):
    value = read(path)
    if value[field] != expected:
        # Only a recorded worker disposition can reject a seed at these boundaries.
        if value[field] not in {"blocked", "reject", "needs_evidence", "reference_work_required"}:
            raise ValueError("Unrecognized worker disposition")
        raise Rejected(stage, "worker_declined", str(path))
    return value


def seal_reference(raw, view, seed):
    from inspect_artifacts import inspect

    result = read(raw / "result.json")
    if result["status"] != "reference_executed_requires_review" or not result["cleanup_verified"]:
        raise ValueError("Reference acceptance or cleanup evidence missing")
    trial = raw / "setup/trials" / str(result["last_passing_test"]["test"])
    frozen = result.get("effective_frozen_directory", "setup/frozen")
    if frozen not in {"setup/frozen", "setup/frozen-runtime-repair"}:
        raise ValueError("Unrecognized effective reference inputs")
    view.mkdir()
    for source, destination in [
        (raw / frozen, view / "inputs"),
        (trial / "candidate", view / "candidate"),
        (trial, view / "trial"),
    ]:
        shutil.copytree(source, destination)
    for name in ("result.json", "outcome.json", "cleanup.json"):
        copy_verified(raw / name, view / name)
    outputs = read(trial / "result.json")["artifacts"]["artifacts"]
    audit = []
    for item in outputs:
        path = view / "trial/outputs" / item["path"]
        if (
            not item["exists"]
            or digest(path) != item["sha256"]
            or path.stat().st_size != item["bytes"]
        ):
            raise ValueError("Reference output identity mismatch")
        audit.append(
            dict(
                file=item["path"],
                bytes=item["bytes"],
                sha256=item["sha256"],
                download_hash_verified=True,
                structural_profile=inspect(path),
            )
        )
    write(view / "provenance.json", seed)
    write(view / "output-audit.json", dict(scope="Structural observations only", outputs=audit))
    write(view / "artifact-manifest.json", dict(files=records(view), large_outputs=outputs))


def seal_materialization(raw, view):
    shutil.copytree(raw / "materialized", view)
    copy_verified(raw / "materialization-candidate.json", view / "candidate.json")
    copy_verified(raw / "result.json", view / "result.json")
    if (raw / "construction-repair.json").exists():
        copy_verified(raw / "construction-repair.json", view / "construction-revision.json")
    write(view / "artifact-manifest.json", dict(original_small_files=records(view)))


def copy_diagnostics(root, destination=Path("/evidence/autonomous-summary")):
    # Small original receipts are also returned through bootstrap diagnostics.
    # Full traces and data remain in the independently verified archive.
    selected = (
        "preparation/plan.json",
        "preparation/result.json",
        "setup-raw/result.json",
        "setup-raw/outcome.json",
        "setup-raw/cleanup.json",
        "replay/result.json",
        "replay/cleanup.json",
        "replay/replay/setup-result.json",
        "specification/specification.json",
        "specification/result.json",
        "specification-review/specification-review.json",
        "specification-review/result.json",
        "specification-revision/specification.json",
        "specification-revision/result.json",
        "specification-review-revised/specification-review.json",
        "specification-review-revised/result.json",
        "specification-review-feedback.json",
        "materialization-raw/result.json",
        "materialization-raw/cleanup.json",
        "materialization-raw/materialization-candidate.json",
        "materialization-raw/materialized/instruction.md",
        "materialization-raw/materialized/rationale.md",
        "grading/result.json",
        "grading/setup-admission.json",
        "grading/cleanup.json",
        "grading/final-candidate.json",
        "grading/final-controls.json",
        "grading/independent-result.json",
        "grading/independent-comparison-conflict.json",
        "grading/review.json",
        "grading/review-repair.json",
        "native/result.json",
    )
    selected += tuple(
        path.replace("grading/", "grading-question-repair/", 1)
        for path in selected
        if path.startswith("grading/")
    )
    selected += tuple(
        path.replace("grading/", "grading-comparison-repair/", 1)
        for path in selected
        if path.startswith("grading/")
    )
    selected += tuple(
        path.replace("grading/", "grading-construction-repair/", 1)
        for path in selected
        if path.startswith("grading/")
    )
    selected += (
        "question-repair/question-repair.json",
        "question-repair/result.json",
        "materialization-question-repair/candidate.json",
        "materialization-question-repair/question-revision.json",
        "comparison-repair/comparison-repair.json",
        "comparison-repair/result.json",
        "grading-comparison-repair/independent-repair-feedback.json",
        "construction-repair-input.json",
        "materialization-repair-raw/result.json",
        "materialization-repair-raw/cleanup.json",
        "materialization-repair-raw/materialization-candidate.json",
        "materialization-repair-raw/construction-repair.json",
    )
    selected += tuple(
        path.relative_to(root).as_posix()
        for path in sorted((root / "setup-raw/setup/trials").glob("*/result.json"))
    )
    for stage in (
        "setup-raw",
        "replay",
        "materialization-raw",
        "grading",
        "grading-question-repair",
        "grading-comparison-repair",
        "materialization-repair-raw",
        "grading-construction-repair",
    ):
        for path in sorted((root / stage / "operations").glob("*/operation.json"))[-3:]:
            selected += (path.relative_to(root).as_posix(),)
            try:
                operation = read(path)
            except (OSError, json.JSONDecodeError):
                # Preserve an interrupted receipt without hiding the primary failure.
                continue
            if operation.get("process", {}).get("exit_code") not in (None, 0):
                selected += ((path.parent / "output.log").relative_to(root).as_posix(),)
    for stage in (
        "preparation",
        "setup-raw",
        "specification",
        "specification-review",
        "specification-revision",
        "specification-review-revised",
        "materialization-raw",
        "grading",
        "materialization-repair-raw",
        "grading-construction-repair",
    ):
        # A one-call author may return a rejected draft without a transport or
        # tool failure. Preserve upstream's actual validation feedback as well
        # as the generic exhausted-allowance error in bounded diagnostics.
        for name in ("draft.json", "operation.json"):
            selected += tuple(
                path.relative_to(root).as_posix()
                for path in sorted((root / stage).glob("*/artifact-stage/" + name))
            )
        selected += tuple(
            path.relative_to(root).as_posix()
            for path in sorted((root / stage).glob("*/artifact-stage/trace/*/failure.json"))[-3:]
        )
    for relative in selected:
        source = root / relative
        if source.is_file() and source.stat().st_size <= 256_000:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


class Pipeline:
    def __init__(self, config, *, root, seed, deadline, endpoint, credential):
        if config.get("entrypoint", "run_autonomous.py") != "run_autonomous.py":
            raise ValueError("Autonomous entrypoint required")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,55}", config["campaign"]):
            raise ValueError("Campaign must be a safe unique identifier")
        path = Path(config["notebook_file"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Notebook must be checkpoint-relative")
        require_full_pipeline_budget(config)
        self.reasoning_effort = native_effort(config)
        self.config, self.root, self.seed = config, root, seed
        self.deadline, self.endpoint, self.credential = deadline, endpoint, credential
        self.prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"]
        self.current = "intake"
        self.receipt = dict(
            status="running",
            autonomous=True,
            operator_interventions=0,
            reasoning_effort_requested=self.reasoning_effort,
            served_endpoint_effective_effort_verified=False,
            source=seed,
            stages=[],
            started=time.time(),
            factory_revision=config["factory_revision"],
            daytona_reserved_usd=0.0,
        )

    def relative(self, path):
        return path.relative_to(HERE).as_posix()

    def config_for(self, name, entrypoint, **extra):
        return dict(
            campaign=self.config["campaign"] + "-" + name,
            entrypoint=entrypoint,
            campaign_seconds=7200,
            cleanup_seconds=300,
            daytona_budget_usd=str(STAGE_RESERVATION_USD),
            setup_seconds=1800,
            reference_seconds=600,
            verifier_seconds=120,
            request_timeout_seconds=600,
            reasoning_effort=self.reasoning_effort,
            command_transport="async_session",
            max_requests=None,
            max_tests=2,
            **({"inspect_review_evidence": True} if entrypoint == "run_notebook_grader.py" else {}),
            **extra,
        )

    async def review_specification(self, *, spec, reference, policy, replay, base, specify):
        """Review before freezing assets; share the single later quality allowance."""
        from specification_inputs import specification_context
        from specification_protocol import SpecificationReview, specification_review_context

        def evidence(**extra):
            return specification_context(
                reference,
                policy,
                inspect_packages=True,
                inspect_reference=True,
                repeatability=read(replay / "result.json"),
                **extra,
            )

        async def call(name, context, **extra):
            destination = self.root / name
            input_file = self.root / (name + "-input.json")
            write(input_file, context)
            await specify(
                self.config_for(
                    name,
                    "run_specification.py",
                    reference_directory=self.relative(reference),
                    policy_file=base["policy_file"],
                    input_file=self.relative(input_file),
                    repeatability_file=self.relative(replay / "result.json"),
                    inspect_packages=True,
                    inspect_reference=True,
                    output_format="tools",
                    **extra,
                ),
                root=destination,
                endpoint=self.endpoint,
                credential=self.credential,
                deadline=self.deadline - 300,
            )
            return destination

        async def review(proposal, name):
            destination = self.root / name
            parent_sha256 = digest(proposal / "specification.json")
            context = specification_review_context(
                evidence(), read(proposal / "specification.json"), parent_sha256=parent_sha256
            )
            entry = {
                "specification_directory": self.relative(proposal),
                "specification_sha256": parent_sha256,
                "review_directory": self.relative(destination),
                "status": "running",
            }
            self.receipt.setdefault("specification_reviews", []).append(entry)
            write(self.root / "pipeline.json", self.receipt)
            await call(
                name,
                context,
                specification_review=True,
                specification_proposal_file=self.relative(proposal / "specification.json"),
            )
            if digest(proposal / "specification.json") != parent_sha256:
                raise ValueError("Specification changed during its review")
            value = SpecificationReview.model_validate(
                read(destination / "specification-review.json")
            )
            entry.update(status="completed", disposition=value.disposition)
            write(self.root / "pipeline.json", self.receipt)
            return value, destination

        initial, review_root = await review(spec, "specification-review")
        if initial.disposition == "reject":
            raise Rejected(
                "specification",
                "scientific_review_rejected",
                str(review_root / "specification-review.json"),
            )
        if initial.disposition == "revise":
            if self.receipt.get("quality_repair"):
                raise Rejected(
                    "specification",
                    "quality_allowance_exhausted",
                    str(review_root / "specification-review.json"),
                )
            self.receipt["quality_repair"] = {
                "kind": "specification_review",
                "target": "task_specification",
                "allowance_consumed": True,
                "original_specification": self.relative(spec),
                "original_review": self.relative(review_root),
            }
            write(self.root / "pipeline.json", self.receipt)
            feedback = {
                "kind": "specification_review_repair",
                "previous_proposal": {
                    key: read(spec / "specification.json")[key]
                    for key in ("task_brief", "validation_handoff")
                },
                "independent_review": initial.model_dump(),
            }
            feedback_file = self.root / "specification-review-feedback.json"
            write(feedback_file, feedback)
            revised = await call(
                "specification-revision",
                evidence(revision_context=feedback),
                revision_context_file=self.relative(feedback_file),
            )
            require_worker(revised / "specification.json", "draft_ready", stage="specification")
            final, final_root = await review(revised, "specification-review-revised")
            self.receipt["quality_repair"].update(
                effective_specification=self.relative(revised),
                effective_review=self.relative(final_root),
                validation_status=final.disposition,
            )
            write(self.root / "pipeline.json", self.receipt)
            if final.disposition != "ready":
                raise Rejected(
                    "specification",
                    "scientific_review_unresolved",
                    str(final_root / "specification-review.json"),
                )
            spec = revised
        self.receipt["effective_specification"] = self.relative(spec)
        return spec

    async def step(self, name, action, *, paid=False):
        self.current = name
        if self.deadline - time.time() < 600:
            raise TimeoutError("Insufficient campaign time for another stage and cleanup")
        if paid:
            if name not in SANDBOX_STAGES:
                raise ValueError("Sandbox stage is absent from the campaign reservation plan")
            reservation = self.receipt["daytona_reserved_usd"] + float(STAGE_RESERVATION_USD)
            if reservation > float(self.config["daytona_budget_usd"]):
                raise TimeoutError("Campaign reservation exhausted")
            self.receipt["daytona_reserved_usd"] = reservation
        record = dict(name=name, status="running", started=time.time())
        self.receipt["stages"].append(record)
        write(self.root / "pipeline.json", self.receipt)
        os.environ["BIOTASKS_ARTIFACT_PREFIX"] = self.prefix + "/stages/" + name
        try:
            await action()
            record["status"] = "completed"
        except Rejected:
            record["status"] = "rejected"
            raise
        except BaseException:
            record["status"] = "incomplete"
            raise
        finally:
            record["finished"] = time.time()
            write(self.root / "pipeline.json", self.receipt)

    async def execute(self):
        from run_preparation import run as prepare
        from run_reference_setup import run as remote
        from run_specification import run as specify
        from specification_inputs import specification_context

        self.root.mkdir(parents=True, exist_ok=False)
        source = HERE / self.config["notebook_file"]
        if digest(source) != self.seed["source_sha256"]:
            raise ValueError("Pinned notebook identity mismatch")
        copy_verified(source, self.root / "source.ipynb")
        intake = self.root / "intake"
        intake.mkdir()
        try:
            subprocess.run(
                [
                    os.environ["BIOTASKS_CONVERSION_PYTHON"],
                    str(HERE / "convert_seed.py"),
                    str(source),
                    str(intake),
                ],
                check=True,
                timeout=120,
            )
            if (intake / "rejection.json").exists():
                raise Rejected(
                    "intake", "unsupported_conversion_profile", str(intake / "rejection.json")
                )
            policy = self.config["task_policy"]
            policy = {**policy}
            policy.setdefault(
                "supplied_intermediates",
                "Allowed with explicit notebook derivation, source identities and stable alignment; preserve substantial source-faithful downstream analysis and withhold its requested answers. Derived assignments are not biological ground truth.",
            )
            policy.setdefault(
                "dependency_answers",
                "GLM must inspect actual installed answer fixtures, declare only verified unused answer-file exclusions with content identities and reasons, and validate the cleaned environment. Preserve required data, scientific methods and original notices; do not expose answer copies through caches or backups.",
            )
            write(self.root / "policy.json", policy)
            prep, setup_raw, reference = [
                self.root / p for p in ("preparation", "setup-raw", "reference")
            ]
            replay, spec, mat_raw, mat, grade = [
                self.root / p
                for p in (
                    "replay",
                    "specification",
                    "materialization-raw",
                    "materialization",
                    "grading",
                )
            ]
            target = dict(
                base_image="python:3.13.13-slim-bookworm",
                gpu=False,
                network="Internet during setup only; reference is offline",
                task_cpus=4,
                task_memory_gib=8,
                task_disk_gib=10,
                reference_seconds=600,
                setup_seconds=1800,
            )

            async def preparation():
                config = self.config_for(
                    "prepare",
                    "run_preparation.py",
                    source_directory=self.relative(intake),
                    target=target,
                )
                config["max_requests"] = 2
                await prepare(
                    config,
                    root=prep,
                    seed=self.seed,
                    endpoint=self.endpoint,
                    credential=self.credential,
                    deadline=self.deadline - 300,
                )
                require_worker(prep / "plan.json", "prepare", stage="preparation")

            await self.step("preparation", preparation)
            base = dict(preparation_directory=self.relative(prep))

            async def setup():
                from run_preparation import repair_runtime_exports

                async def repair_exports(feedback, *, deadline):
                    return await repair_runtime_exports(
                        original=prep,
                        feedback=feedback,
                        endpoint=self.endpoint,
                        credential=self.credential,
                        deadline=deadline,
                    )

                result = await remote(
                    self.config_for("setup", "run_reference_setup.py", **base),
                    root=setup_raw,
                    deadline=self.deadline,
                    endpoint=self.endpoint,
                    credential=self.credential,
                    repair_exports=repair_exports,
                )
                effective = result.get("effective_preparation_directory")
                if effective is not None:
                    effective = Path(effective)
                    if effective.resolve() != (prep / "runtime-repair").resolve():
                        raise ValueError("Unexpected effective preparation directory")
                    base["preparation_directory"] = self.relative(effective)
                require_worker(setup_raw / "outcome.json", "tested", stage="setup")
                seal_reference(setup_raw, reference, self.seed)

            await self.step("setup", setup, paid=True)
            base["reference_directory"] = self.relative(reference)

            async def repeat():
                result = await remote(
                    self.config_for("replay", "run_reference_replay.py", **base),
                    root=replay,
                    deadline=self.deadline,
                    endpoint=None,
                    credential=None,
                )
                if result["status"] != "repeatability_observed_requires_comparison_review":
                    raise ValueError("Replay did not produce complete observations")
                # Repeatability is evidence for scientific validation, not a byte gate.
                # Successful executions with differing outputs still need semantic review.

            await self.step("replay", repeat, paid=True)
            base.update(
                replay_directory=self.relative(replay),
                policy_file=self.relative(self.root / "policy.json"),
            )

            async def specification():
                nonlocal spec
                context = specification_context(
                    reference,
                    policy,
                    inspect_packages=True,
                    inspect_reference=True,
                    repeatability=json.loads((replay / "result.json").read_text()),
                )
                write(self.root / "specification-input.json", context)
                config = self.config_for(
                    "specification",
                    "run_specification.py",
                    reference_directory=self.relative(reference),
                    policy_file=base["policy_file"],
                    input_file=self.relative(self.root / "specification-input.json"),
                    repeatability_file=self.relative(replay / "result.json"),
                    inspect_packages=True,
                    inspect_reference=True,
                    output_format="tools",
                )
                await specify(
                    config,
                    root=spec,
                    endpoint=self.endpoint,
                    credential=self.credential,
                    deadline=self.deadline - 300,
                )
                require_worker(spec / "specification.json", "draft_ready", stage="specification")
                (spec / "README.md").write_text(
                    "Automatic handoff of the unchanged worker proposal. No operator review or additional scientific instructions.\n"
                )
                spec = await self.review_specification(
                    spec=spec,
                    reference=reference,
                    policy=policy,
                    replay=replay,
                    base=base,
                    specify=specify,
                )

            await self.step("specification", specification)
            base["specification_directory"] = self.relative(spec)

            async def construct():
                target_dir = Path("/work/grading-inputs/reference-replay/replay/trials/1/outputs")
                shutil.copytree(reference / "trial/outputs", target_dir)
                config = self.config_for(
                    "construct", "run_notebook_grader.py", **base, materialize_task=True
                )
                config["max_tests"] = None
                result = await remote(
                    config,
                    root=mat_raw,
                    deadline=self.deadline,
                    endpoint=self.endpoint,
                    credential=self.credential,
                )
                if result["status"] == "materialization_blocked":
                    raise Rejected(
                        "construction",
                        "worker_declined",
                        str(mat_raw / "materialization-candidate.json"),
                    )
                seal_materialization(mat_raw, mat)

            await self.step("construction", construct, paid=True)
            base["materialization_directory"] = self.relative(mat)

            async def grading():
                nonlocal mat_raw, mat, grade
                shutil.copytree(
                    mat_raw / "materialized", Path("/work/grading-inputs/grading/materialized")
                )
                config = self.config_for("grading", "run_notebook_grader.py", **base)
                config["allow_quality_repair"] = not bool(self.receipt.get("quality_repair"))
                config["max_tests"] = None
                result = await remote(
                    config,
                    root=grade,
                    deadline=self.deadline,
                    endpoint=self.endpoint,
                    credential=self.credential,
                )
                if (
                    result["status"] == "grader_blocked"
                    and not (grade / "repair.json").exists()
                    and not self.receipt.get("quality_repair")
                ):
                    from construction_repair import repair_context as construction_context

                    feedback = construction_context(mat_raw, mat, grade)
                    self.receipt["quality_repair"] = {
                        "kind": "generated_construction",
                        "allowance_consumed": True,
                        "original_materialization": self.relative(mat),
                        "original_grading": self.relative(grade),
                    }
                    write(self.root / "pipeline.json", self.receipt)
                    feedback_file = self.root / "construction-repair-input.json"
                    write(feedback_file, feedback)
                    mat_raw = self.root / "materialization-repair-raw"
                    repair_base = {
                        key: value
                        for key, value in base.items()
                        if key != "materialization_directory"
                    }
                    retry = self.config_for(
                        "construction-repair",
                        "run_notebook_grader.py",
                        **repair_base,
                        materialize_task=True,
                        allow_quality_repair=False,
                        construction_repair_file=self.relative(feedback_file),
                        construction_repair_directory=self.relative(mat),
                    )
                    retry["max_tests"] = None
                    os.environ["BIOTASKS_ARTIFACT_PREFIX"] = (
                        self.prefix + "/stages/construction-repair"
                    )
                    repaired = await remote(
                        retry,
                        root=mat_raw,
                        deadline=self.deadline,
                        endpoint=self.endpoint,
                        credential=self.credential,
                    )
                    if repaired["status"] == "materialization_blocked":
                        raise Rejected(
                            "grading", "construction_repair_blocked", str(mat_raw / "result.json")
                        )
                    mat = self.root / "materialization-repair"
                    seal_materialization(mat_raw, mat)
                    # These are task-owned transport copies, not original evidence.
                    # Keep both sealed constructions and all earlier grading unchanged.
                    staged = Path("/work/grading-inputs/grading/materialized")
                    shutil.rmtree(staged)
                    shutil.copytree(mat_raw / "materialized", staged)
                    grade = self.root / "grading-construction-repair"
                    base["materialization_directory"] = self.relative(mat)
                    retry = self.config_for(
                        "grading-construction-repair",
                        "run_notebook_grader.py",
                        **base,
                        allow_quality_repair=False,
                    )
                    retry["max_tests"] = None
                    os.environ["BIOTASKS_ARTIFACT_PREFIX"] = (
                        self.prefix + "/stages/grading-construction-repair"
                    )
                    result = await remote(
                        retry,
                        root=grade,
                        deadline=self.deadline,
                        endpoint=self.endpoint,
                        credential=self.credential,
                    )
                    self.receipt["quality_repair"].update(
                        effective_materialization=self.relative(mat),
                        effective_grading=self.relative(grade),
                        validation_status=result["status"],
                    )
                if (
                    result["status"]
                    in {"independent_comparison_unresolved", "public_question_defect"}
                    and not (grade / "repair.json").exists()
                    and not self.receipt.get("quality_repair")
                ):
                    from comparison_repair import (
                        freeze_comparison_revision,
                        independent_repair_record,
                        validate_diagnosis,
                    )
                    from question_repair import repair_context, revise_question

                    revision_context = repair_context(mat, grade)
                    self.receipt["quality_repair"] = {
                        "kind": "public_question_diagnosis"
                        if result["status"] == "public_question_defect"
                        else "comparison_diagnosis",
                        "allowance_consumed": True,
                        "original_materialization": self.relative(mat),
                        "original_grading": self.relative(grade),
                    }
                    write(self.root / "pipeline.json", self.receipt)
                    write(self.root / "comparison-repair-evidence.json", revision_context)
                    context = specification_context(
                        reference,
                        policy,
                        inspect_packages=True,
                        inspect_reference=True,
                        repeatability=read(replay / "result.json"),
                        revision_context=revision_context,
                    )
                    write(self.root / "comparison-repair-input.json", context)
                    repair_root = self.root / "comparison-repair"
                    await specify(
                        self.config_for(
                            "comparison-repair",
                            "run_specification.py",
                            reference_directory=self.relative(reference),
                            policy_file=base["policy_file"],
                            input_file=self.relative(self.root / "comparison-repair-input.json"),
                            repeatability_file=self.relative(replay / "result.json"),
                            revision_context_file=self.relative(
                                self.root / "comparison-repair-evidence.json"
                            ),
                            comparison_repair=True,
                            inspect_packages=True,
                            inspect_reference=True,
                            output_format="tools",
                        ),
                        root=repair_root,
                        endpoint=self.endpoint,
                        credential=self.credential,
                        deadline=self.deadline - 300,
                    )
                    response = read(repair_root / "comparison-repair.json")
                    require_worker(repair_root / "comparison-repair.json", "ready", stage="grading")
                    diagnosis = validate_diagnosis(response, revision_context)
                    self.receipt["quality_repair"]["target"] = diagnosis.target
                    independent_file = None
                    if diagnosis.target == "public_question":
                        revised = self.root / "materialization-question-repair"
                        revise_question(
                            mat,
                            revised,
                            {
                                "disposition": "ready",
                                "instruction": diagnosis.instruction,
                                "rationale": diagnosis.rationale,
                            },
                        )
                        mat = revised
                    else:
                        independent_file = self.root / "independent-repair-input.json"
                        write(
                            independent_file,
                            independent_repair_record(revision_context, diagnosis),
                        )
                    grade = self.root / "grading-comparison-repair"
                    base["materialization_directory"] = self.relative(mat)
                    write(
                        self.root / "comparison-repair-frozen-grader.json",
                        freeze_comparison_revision(
                            read(mat / "candidate.json"), revision_context, diagnosis
                        ),
                    )
                    # Fresh isolated validation never receives private diagnostic
                    # reasoning or answers. Independent repairs add only the
                    # worker's own code and exact public/prior-code quotes.
                    retry = self.config_for(
                        "grading-comparison-repair",
                        "run_notebook_grader.py",
                        **base,
                        allow_quality_repair=False,
                        review_observation_directories=[
                            self.receipt["quality_repair"]["original_grading"]
                        ],
                        frozen_grader_file=self.relative(
                            self.root / "comparison-repair-frozen-grader.json"
                        ),
                        **(
                            {"independent_repair_file": self.relative(independent_file)}
                            if independent_file
                            else {}
                        ),
                    )
                    retry["max_tests"] = None
                    os.environ["BIOTASKS_ARTIFACT_PREFIX"] = (
                        self.prefix + "/stages/grading-comparison-repair"
                    )
                    result = await remote(
                        retry,
                        root=grade,
                        deadline=self.deadline,
                        endpoint=self.endpoint,
                        credential=self.credential,
                    )
                    self.receipt["quality_repair"].update(
                        effective_materialization=self.relative(mat),
                        effective_grading=self.relative(grade),
                        validation_status=result["status"],
                    )
                if result["status"] != "grader_candidate_validated" or not result.get(
                    "final_controls_passed"
                ):
                    allowed = {
                        "independent_comparison_unresolved",
                        "independent_solution_blocked",
                        "grader_blocked",
                        "probe_author_blocked",
                        "repair_blocked",
                        "grader_requires_further_work",
                        "question_review_blocked",
                        "public_question_defect",
                    }
                    if result["status"] not in allowed:
                        raise ValueError("Unrecognized validation outcome")
                    raise Rejected("grading", result["status"], str(grade / "result.json"))

            await self.step("grading", grading, paid=True)
            self.receipt.update(
                effective_materialization=self.relative(mat), effective_grading=self.relative(grade)
            )

            async def native():
                from run_scientific_native import run

                native_root = self.root / "native"
                native_root.mkdir()
                shutil.copytree(mat, native_root / "materialized")
                from release_metadata import campaign_attribution

                write(
                    self.root / "attribution.json",
                    campaign_attribution(self.config, self.seed, mat, experiment_root=HERE),
                )
                config = self.config_for(
                    "native",
                    "run_scientific_native.py",
                    **base,
                    grading_directory=self.relative(grade),
                    attribution_file=self.relative(self.root / "attribution.json"),
                    task_name=self.config["campaign"],
                    factory_revision=self.config["factory_revision"],
                )
                result = await asyncio.to_thread(run, config, root=native_root)
                if not result["publication_ready"]:
                    raise RuntimeError("Native infrastructure failed; not a notebook rejection")

            await self.step("native", native, paid=True)
            self.receipt.update(
                status="validated", task_directory=self.relative(self.root / "native/tasks")
            )
        except Rejected as exc:
            self.receipt.update(
                status="rejected",
                rejection=dict(
                    stage=exc.stage,
                    reason=exc.reason,
                    evidence=str(Path(exc.evidence).relative_to(self.root)),
                ),
            )
        except BaseException as exc:
            self.receipt.update(
                status="infrastructure_failed",
                failed_stage=self.current,
                error_type=type(exc).__name__,
            )
            raise
        finally:
            self.receipt["finished"] = time.time()
            write(self.root / "pipeline.json", self.receipt)
            os.environ["BIOTASKS_ARTIFACT_PREFIX"] = self.prefix
            shutil.copyfile(self.root / "pipeline.json", "/evidence/autonomous-result.json")
            copy_diagnostics(self.root)
            from iris_bootstrap import export_on_host

            # Every stage has returned and closed its writers. The final archive
            # reuses the fully checked snapshot transport instead of issuing an
            # object upload/readback for every trace file. No execution extension.
            await asyncio.to_thread(
                export_on_host,
                self.root,
                self.prefix + "/autonomous-snapshot",
                deadline=self.deadline,
                snapshot=True,
            )
        return self.receipt


if __name__ == "__main__":
    config = read(os.environ["BIOTASKS_CONFIG"])
    config["factory_revision"] = read("/evidence/inputs.json")["factory_revision"]
    result = asyncio.run(
        Pipeline(
            config,
            root=HERE / "autonomous-work" / config["campaign"],
            seed=read(os.environ["BIOTASKS_SEED"])[0],
            deadline=float(os.environ["BIOTASKS_CAMPAIGN_DEADLINE"]),
            endpoint=os.environ["BIOTASKS_MODEL_ENDPOINT"],
            credential=os.environ["GLM_BULK_TOKEN"],
        ).execute()
    )
    print(json.dumps(result))
