"""Build native task exports and exercise fresh-container grading controls.

Development harness, not a production service. Target code only runs through
the caller's bounded Docker wrapper. Native reward is recorded separately from
the additional acceptance checks.
"""

import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import shlex
import tarfile
import tempfile
import time
from pathlib import Path


def pytest_statuses(parser, log):
    """Exclude application logger lines misrecognized by the native parser."""
    return {key: value for key, value in parser("pytest", log).items()
            if re.match(r"^[^\s:]+\.py(?:::|$)", key)}


def baseline_assertion_gate(outcome, parser):
    statuses = pytest_statuses(parser, outcome.pre_log)
    return bool(
        outcome.fail_to_pass and outcome.pass_to_pass
        and all(statuses.get(t) == "FAILED" for t in outcome.fail_to_pass)
        and "ERROR" not in statuses.values()
        and "ERROR collecting" not in outcome.pre_log
        and re.search(r"AssertionError|DID NOT RAISE|^E\s+assert ", outcome.pre_log,
                      flags=re.MULTILINE)
    )


def controls_passed(controls, baseline_gate):
    by_name = {c["name"]: c for c in controls}
    return bool(
        baseline_gate and by_name["reference"]["strict_reference_pass"]
        and all(c.get("disposition") == "graded" and
                c.get("details", {}).get("resolved") is False and
                c.get("details", {}).get("reward", 1) < 1
                for c in controls if c["name"] != "reference")
    )


def verify_export(native_docker, manifest, row, outcome, bootstrap, out):
    from repo2rlenv.emitter.harbor import write_harbor_task
    from repo2rlenv.github import PullRequestSummary
    from repo2rlenv.pipelines.pr_runtime import (
        PRRuntimePipeline, _files_in_patch, split_patch_and_test_patch,
    )
    from repo2rlenv.spec.input import GenerationInput
    from repo2rlenv.spec.options import PRRuntimeOptions

    started = time.monotonic()
    result = {"controls": [], "accepted": False}
    patch, tests = split_patch_and_test_patch(row["diff"])
    metadata = row["metadata"]
    pr = PullRequestSummary(
        number=row["number"], title=metadata["title"], body=metadata["body"],
        state="MERGED", merged_at=metadata["mergedAt"], base_ref="",
        base_sha=row["base_sha"], head_sha=row["head_sha"], is_draft=False,
        url=row["url"], changed_files=_files_in_patch(row["diff"]),
    )
    spec = GenerationInput.model_validate({
        "repo": {"url": manifest["repository"], "ref": row["base_sha"], "access": "public"},
        "pipeline": {"name": "pr_runtime"},
        "output": {"destination": str(out), "org": "biotasks-research",
                   "dataset_name": "issue-24-development", "visibility": "private"},
    })
    pipeline = PRRuntimePipeline(spec, PRRuntimeOptions(), bootstrap)

    class CachedIssues:
        @staticmethod
        def fetch_issue(owner, name, number, token=None):
            cached = row["linked_issues"].get(str(number))
            if cached is None:
                raise RuntimeError(f"Linked issue {number} missing from frozen inputs")
            return cached["title"], cached["body"]

    pipeline._provider = CachedIssues
    task = pipeline._build_task(
        pr, patch, tests, fail_to_pass=outcome.fail_to_pass,
        pass_to_pass=outcome.pass_to_pass, validation_status=outcome.status,
    )
    image_tag = f"biotasks24/{manifest['run_id']}:{row['number']}"
    sandbox = None
    try:
        with tempfile.TemporaryDirectory() as directory:
            task_root = write_harbor_task(task, Path(directory) / "task")
            # Preserve exact emitted bytes in a flat outer Iris artifact.
            with tarfile.open(out / f"task-{row['number']}.tar.gz", "w:gz") as bundle:
                bundle.add(task_root, arcname="task")
            result["instruction"] = task.instruction
            build = native_docker._run([
                "docker", "build", "--network", "iris-egress", "--memory", "8g",
                "--memory-swap", "8g", "--cpu-period", "100000", "--cpu-quota", "200000",
                "--label", f"biotasks24.run={manifest['run_id']}", "--rm", "--force-rm",
                "-t", image_tag, str(task_root / "environment"),
            ], timeout=300)
            (out / f"build-{row['number']}.json").write_text(
                json.dumps(dataclasses.asdict(build), indent=2) + "\n"
            )
            result["build_exit_code"] = build.exit_code
            if not build.ok:
                result["reason"] = "exported_environment_build_failed"
                return result
            image = native_docker._run(
                ["docker", "image", "inspect", image_tag, "--format", "{{.Id}}"], timeout=15
            )
            result["image_id"] = image.stdout.strip()
            verifier_file = task_root / "tests/verifier.py"
            verifier_spec = importlib.util.spec_from_file_location("exported_verifier", verifier_file)
            verifier = importlib.util.module_from_spec(verifier_spec)
            verifier_spec.loader.exec_module(verifier)

            result["baseline_assertion_gate"] = baseline_assertion_gate(outcome, verifier.parse_logs)
            chunks = re.split(r"(?=^diff --git )", patch, flags=re.MULTILINE)
            chunks = [chunk for chunk in chunks if chunk.strip()]
            ranked = sorted(
                enumerate(chunks), key=lambda pair: hashlib.sha256(pair[1].encode()).hexdigest()
            )[:5]
            controls = [("base", ""), ("reference", patch)]
            controls += [
                (f"omit-source-{index}", "".join(c for i, c in enumerate(chunks) if i != index))
                for index, _ in ranked
            ]
            controls += [("base-with-tests-deleted", "")]
            os.environ["BIOTASKS24_OFFLINE"] = "1"
            for name, candidate_patch in controls:
                remaining = int(1800 - (time.monotonic() - started))
                if remaining <= 15:
                    raise TimeoutError("Per-PR export/control budget exhausted")
                empty = Path(directory) / "empty"
                empty.mkdir(exist_ok=True)
                sandbox = native_docker.DockerSandbox.start(image_tag, empty)
                # Solver phase has neither tests nor oracle files, and no network.
                isolation = sandbox.exec(
                    "test ! -e /tests && test ! -e /solution && "
                    "test ! -S /var/run/docker.sock && "
                    "git rev-list --all --count && git status --porcelain",
                    timeout=15,
                )
                control = {"name": name, "isolation_exit_code": isolation.exit_code,
                           "history_and_status": isolation.stdout}
                if not isolation.ok or isolation.stdout.strip() != "1":
                    raise RuntimeError("Solver input isolation check failed")
                if candidate_patch:
                    applied = sandbox.exec(
                        "git apply - <<'BIOTASKS24_CANDIDATE'\n" + candidate_patch
                        + "\nBIOTASKS24_CANDIDATE", timeout=30,
                    )
                    control["candidate_apply_exit_code"] = applied.exit_code
                    if not applied.ok:
                        control["disposition"] = "unresolved_patch_control"
                        result["controls"].append(control)
                        sandbox.cleanup()
                        sandbox = None
                        continue
                if name == "base-with-tests-deleted":
                    removed = sandbox.exec(
                        "rm -f -- " + " ".join(shlex.quote(p) for p in _files_in_patch(tests)),
                        timeout=15,
                    )
                    if not removed.ok:
                        raise RuntimeError("Test deletion control failed")
                copied = native_docker._run([
                    "docker", "cp", str(task_root / "tests"),
                    f"{sandbox.container_id}:/tests",
                ], timeout=30)
                if not copied.ok:
                    raise RuntimeError("Cannot stage verifier")
                graded = sandbox.exec("bash /tests/test.sh", timeout=min(300, remaining - 10))
                details = sandbox.exec("cat /logs/verifier/reward-details.json", timeout=15)
                control.update(
                    grader_exit_code=graded.exit_code,
                    details=json.loads(details.stdout) if details.ok else None,
                )
                statuses = pytest_statuses(verifier.parse_logs, graded.stdout)
                control["statuses"] = statuses
                d = control["details"] or {}
                control["strict_reference_pass"] = bool(
                    d.get("command_resolved") and d.get("exit_code") == 0
                    and outcome.fail_to_pass and outcome.pass_to_pass
                    and all(statuses.get(t) == "PASSED"
                            for t in outcome.fail_to_pass + outcome.pass_to_pass)
                    and not any(v in ("FAILED", "ERROR") for v in statuses.values())
                )
                control["disposition"] = "graded"
                (out / f"control-{row['number']}-{name}.json").write_text(
                    json.dumps(dataclasses.asdict(graded), indent=2) + "\n"
                )
                result["controls"].append(control)
                sandbox.cleanup()
                sandbox = None
            result["controls_passed"] = controls_passed(
                result["controls"], result["baseline_assertion_gate"],
            )
            # Independent instruction/biology audit is an additional gate.
            result["reason"] = "pending_independent_audit" if result["controls_passed"] else "control_failure"
    except Exception as exc:
        result["reason"] = "export_or_control_error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        os.environ.pop("BIOTASKS24_OFFLINE", None)
        if sandbox is not None:
            sandbox.cleanup()
        removal = native_docker._run(["docker", "image", "rm", image_tag], timeout=30)
        result["image_tag_removed"] = removal.ok
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (out / f"export-{row['number']}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
