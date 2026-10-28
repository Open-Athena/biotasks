"""Review captured Harbor evidence before admitting a generated scientific task.

Reuses upstream trial binding, Review schema and rollout-outcome checks. This
worker has read-only evidence tools, never a shell, grader or repair authority.
"""

import hashlib
import json
import time
from pathlib import Path

import httpx
from admission_profile import NATIVE_REVIEW_PROFILE
from design_stage import completion_transport
from model_profile import native_effort
from openai import AsyncOpenAI
from reference_stage import stage
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.artifacts import import_trial
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.quality.loop.context import EvidenceContext
from repo2rlenv.quality.loop.models import Review
from repo2rlenv.quality.loop.runner import control_failures, validate_rollout_outcome
from repo2rlenv.tasksmith.author.budget import AuthorBudget
from review_packet import ReviewPacket

from biotasks.chat_author import ChatLimits
from biotasks.inference_gate import Allowance, RequestLedger


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_path(root, relative):
    """Accept only regular evidence under the caller's explicit owned root."""
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Native evidence path escapes its root")
    path = root / relative
    if (
        any(part.is_symlink() for part in (path, *path.parents))
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise ValueError("Native evidence must be a regular unlinked file")
    return path


def collect(native):
    """Freeze whole text documents; binary files retain identities, not guesses.

    No excerpt size cap, scientific ranking, extension filter or operator defect
    hint. All captured solver commands/results are inspectable. Native trial
    checksums bind the reference, baseline and solver to the same task bytes.
    """
    native = Path(native)
    summary_path = checked_path(native, "result.json")
    summary = json.loads(summary_path.read_text())
    if summary.get("status") != "native_validated_solver_attempt_recorded":
        raise ValueError("Native execution has not completed")
    tasks = native / "tasks"
    if tasks.is_symlink() or not tasks.is_dir():
        raise ValueError("Native task directory is unavailable")
    task_dirs = list(tasks.iterdir())
    if len(task_dirs) != 1 or not task_dirs[0].is_dir() or task_dirs[0].is_symlink():
        raise ValueError("Review requires exactly one native task")
    task = task_dirs[0]
    identity = inspect_bundle(task)
    if not identity["integrity_passed"]:
        raise ValueError("Native task integrity failed")
    archived = json.loads(checked_path(native, "package/identity.json").read_text())
    if identity != archived:
        raise ValueError("Native task differs from the pre-trial package")
    if len(summary.get("controls", [])) != 2 or not isinstance(summary.get("solver"), dict):
        raise ValueError("Require reference, empty baseline and one blind attempt")
    rows = [*summary["controls"], summary["solver"]]
    trials, documents, inventory = [], {}, []

    def include(key, path):
        path = checked_path(native, path.relative_to(native))
        before = digest(path)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != before:
            raise ValueError("Evidence changed during collection")
        try:
            text = raw.decode("utf-8")
            if "\0" in text:
                text = None
        except UnicodeError:
            text = None
        if text is not None:
            documents[key] = text
        inventory.append(
            dict(
                key=key,
                path=path.relative_to(native).as_posix(),
                sha256=before,
                bytes=len(raw),
                mode=path.stat().st_mode & 0o7777,
                text_available=text is not None,
            )
        )

    include("native/result.json", summary_path)
    include("native/package-identity.json", native / "package/identity.json")
    for path in sorted(task.rglob("*")):
        if path.is_symlink():
            raise ValueError("Task evidence contains a link")
        if path.is_file():
            include("task/" + path.relative_to(task).as_posix(), path)
    for index, (role, row) in enumerate(zip(("oracle", "baseline", "rollout"), rows, strict=True)):
        if row.get("cleanup_verified") is not True:
            raise ValueError("Native trial cleanup has not been verified")
        path = checked_path(native, row["result_path"])
        trial = import_trial(path, task, role)
        if (
            trial.bundle_hash != identity["bundle_hash"]
            or trial.reward != row["reward"]
            or trial.agent != row["agent"]
            or trial.exception_type != row["exception_type"]
        ):
            raise ValueError("Native summary contradicts bound trial evidence")
        trials.append(trial)
        prefix = f"evidence/{index}-{role}/"
        for item in sorted(path.parent.rglob("*")):
            if item.is_symlink():
                raise ValueError("Trial evidence contains a link")
            if item.is_file():
                include(prefix + item.relative_to(path.parent).as_posix(), item)
    if control_failures(trials, 1.0):
        raise ValueError("Native reference/baseline contrast is invalid")
    recheck(native, inventory)
    return dict(
        bundle_hash=identity["bundle_hash"], documents=documents, inventory=inventory
    ), trials


def recheck(native, inventory):
    """Frozen review text cannot authorize publication of changed source bytes."""
    for row in inventory:
        path = checked_path(native, row["path"])
        if (
            path.stat().st_size != row["bytes"]
            or path.stat().st_mode & 0o7777 != row["mode"]
            or digest(path) != row["sha256"]
        ):
            raise ValueError("Native evidence identity changed after collection")
    roots = {native / "tasks"}
    roots.update(
        (native / row["path"]).parent
        for row in inventory
        if row["key"].startswith("evidence/")
        and row["key"].count("/") == 2
        and row["key"].endswith("/result.json")
    )
    recorded = {row["path"] for row in inventory}
    for root in roots:
        for path in root.rglob("*"):
            if path.is_symlink() or (not path.is_dir() and not path.is_file()):
                raise ValueError("Native evidence tree contains a link or special file")
            if path.is_file() and path.relative_to(native).as_posix() not in recorded:
                raise ValueError("Native evidence tree gained an unreviewed file")


def validate(review, evidence, trials):
    """Validate citations and outcome consistency; the model never changes reward."""
    if review.probes or review.read_requests:
        raise ValueError("Use read-only packet tools; no new probe or deferred read request")
    # Reuse upstream's citation validation without its size-limited collector.
    context = EvidenceContext.__new__(EvidenceContext)
    context.documents = evidence["documents"]
    context.validate_review(review)
    validate_rollout_outcome(review, trials, 1.0)
    if review.rollout in {"task_defect", "reward_hack"} and not any(
        issue.severity == "blocking" for issue in review.issues
    ):
        raise ValueError("A task defect or reward hack requires a grounded blocking issue")
    if review.rollout in {"legitimate_success", "legitimate_failure"}:
        citations = [
            cite
            for item in (review.task, review.verifier, review.leakage, *review.issues)
            for cite in item.evidence
        ]
        paths = {cite.path for cite in citations}
        if "task/instruction.md" not in paths:
            raise ValueError("A legitimate outcome requires the public contract")
        if not any(p.startswith("evidence/2-rollout/verifier/") for p in paths):
            raise ValueError("A legitimate outcome requires actual verifier evidence")
        if "evidence/2-rollout/agent/trajectory.json" not in paths:
            raise ValueError("A legitimate outcome requires captured solver execution evidence")


def admission(review):
    """A failed solver may be legitimate; unknown or defective contracts cannot pass."""
    if review.sound and review.rollout in {"legitimate_success", "legitimate_failure"}:
        return "validated"
    if review.rollout == "infrastructure_failure":
        return "infrastructure_failed"
    if review.rollout in {"task_defect", "reward_hack"} or any(
        issue.severity == "blocking" for issue in review.issues
    ):
        return "rejected"
    return "needs_evidence"


async def run(config, *, native, root, endpoint, credential, deadline, complete=None):
    """One read-only GLM review session within the existing campaign deadline.

    No new computation, sandbox, solver attempt or repair is dispatched. A stop
    preserves the native reward and feeds general factory development later.
    """
    evidence, trials = collect(native)
    root.mkdir(parents=True, exist_ok=False)
    save_record(root / "configuration.json", config)
    save_record(root / "input.json", evidence)
    packet = ReviewPacket(root / "review-packets", evidence, deadline)
    ledger = RequestLedger(root / "requests.sqlite", {"native_review": Allowance(None, None)})
    budget = RunBudget(BudgetLedger(root / "model-budget.sqlite", limit_usd="1"), "review", "1")
    limits = ChatLimits(
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort=native_effort(config),
        request_timeout_sec=config["request_timeout_seconds"],
    )
    client = None
    result = dict(
        status="incomplete",
        profile=NATIVE_REVIEW_PROFILE,
        started=time.time(),
        bundle_hash=evidence["bundle_hash"],
    )
    try:
        if complete is None:
            client = AsyncOpenAI(
                base_url=endpoint,
                api_key=credential,
                max_retries=0,
                timeout=limits.request_timeout_sec,
                http_client=httpx.AsyncClient(follow_redirects=False),
            )
            complete = completion_transport(client)

        async def validate_response(value):
            recheck(native, evidence["inventory"])
            validate(value, evidence, trials)

        review = await stage(
            schema=Review,
            name="native_review",
            prompt_name="notebook-native-review",
            context=packet.model_context,
            root=root / "review",
            ledger=ledger,
            budget=AuthorBudget(budget, root / "charges", "native_review"),
            complete=complete,
            deadline=deadline,
            limits=limits,
            max_requests=None,
            output_format="tools",
            validate=validate_response,
            recover_output_limit=False,
            extra_tools=packet.tools,
            extra_handlers=packet.handlers,
        )
        recheck(native, evidence["inventory"])
        save_record(root / "review.json", review.model_dump())
        result.update(status=admission(review), rollout=review.rollout)
    finally:
        if client is not None:
            await client.close()
        result["finished"] = time.time()
        save_record(root / "result.json", result)
    return result


def check_recorded(native, profile, bundle_hash):
    """Revalidate a completed review from original evidence; no model invocation."""
    if profile != NATIVE_REVIEW_PROFILE:
        raise ValueError("A known explicit native-review profile is required")
    native = Path(native)
    root = native.parent / "native-review"
    identities = {}

    def recorded(relative):
        path = checked_path(root, relative)
        identities["native-review/" + relative] = digest(path)
        return json.loads(path.read_text())

    result = recorded("result.json")
    if (
        result.get("status") != "validated"
        or result.get("profile") != profile
        or result.get("bundle_hash") != bundle_hash
    ):
        raise ValueError("Native contract review is incomplete, rejected or for another bundle")
    evidence, trials = collect(native)
    if evidence["bundle_hash"] != bundle_hash or recorded("input.json") != evidence:
        raise ValueError("Native review input differs from this task and its captured trials")
    review = Review.model_validate(recorded("review.json"))
    artifact = recorded("review/artifact-stage/artifact.json")
    if artifact.get("artifact") != review.model_dump():
        raise ValueError("Native review differs from the worker's recorded submission")
    inputs = recorded("review/input.json")
    packet = ReviewPacket.open_recorded(
        root / "review-packets", inputs.get("review_evidence"), deadline=time.time() + 60
    )
    if packet.reconstruct() != evidence:
        raise ValueError("Native review packet differs from its original inputs")
    inline = {k: v for k, v in evidence.items() if k in ReviewPacket.INLINE_FIELDS}
    if {k: v for k, v in inputs.items() if k != "review_evidence"} != inline:
        raise ValueError("Native review inline context differs from its packet")
    for path in sorted(packet.root.iterdir()):
        relative = path.relative_to(root).as_posix()
        recorded(relative)
    validate(review, evidence, trials)
    if admission(review) != "validated" or result.get("rollout") != review.rollout:
        raise ValueError("Native review does not establish a legitimate sound outcome")
    recheck(native, evidence["inventory"])
    return {
        "profile": profile,
        "bundle_hash": bundle_hash,
        "review": review.model_dump(),
        "result": result,
        "evidence_files": identities,
        "context_sha256": packet.context_sha256,
        "original_rewards": [trial.reward for trial in trials],
        "scope": "Revalidated recorded review; no new model call or reward change.",
    }
