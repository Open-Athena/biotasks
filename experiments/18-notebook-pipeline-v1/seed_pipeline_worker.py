"""Run one seed through the frozen factory, preserving every bounded stage.

The campaign reserves this seed before submission and never retries an uncertain
job. This process has no per-notebook branches and never edits scientific tasks.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import fsspec
from zcode_smoke import export_files

from biotasks.factory_acceptance import acceptance
from biotasks.factory_controller import NativeEvidence, WorkerEvidence, decide
from biotasks.factory_native import candidate_hash, file_hash, reward_for, subgoal_weights
from biotasks.factory_proposal import proposal_action


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


class SeedPipeline:
    def __init__(self, root):
        self.root = root
        self.plan = json.loads((root / "pipeline.json").read_text())
        self.prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
        self.started = time.monotonic()
        self.stages = []
        self.accepted = False
        self.secrets = [
            value
            for key, value in os.environ.items()
            if key in {"GLM_BULK_TOKEN", "DAYTONA_API_KEY", "BIOTASKS_ARTIFACT_PREFIX"} and value
        ]

    def upload(self, path, relative):
        """Stream and verify artifacts; no credential values enter the manifest."""
        uri = self.prefix + "/" + relative
        with path.open("rb") as source, fsspec.open(uri, "wb").open() as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
        digest = hashlib.sha256()
        with fsspec.open(uri, "rb").open() as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != file_hash(path):
            raise ValueError("Pipeline checkpoint read-back mismatch")

    def checkpoint(self, status, **extra):
        path = self.root / "pipeline-summary.json"
        value = {
            "schema_version": 1,
            "seed": self.plan["seed"],
            "factory_revision": self.plan["factory_revision"],
            "status": status,
            "stages": self.stages,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
            **extra,
        }
        write_json(path, value)
        self.upload(path, "pipeline-summary.json")
        print("BIOTASKS_PIPELINE " + json.dumps(value), flush=True)
        return value

    def command(self, command, directory, seconds, env):
        remaining = self.plan["seed_timeout_seconds"] - (time.monotonic() - self.started) - 120
        if remaining < 30:
            raise TimeoutError("Seed execution budget exhausted before stage launch")
        with (directory / "launcher.log").open("wb") as output:
            child = subprocess.Popen(
                command,
                cwd=directory,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                child.wait(timeout=min(seconds, remaining))
            finally:
                if child.returncode is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        if child.returncode:
            raise RuntimeError("Stage launcher failed; preserve its records for diagnosis")

    def inputs(self, workspace, output, slot, native=None):
        selected, _ = export_files(workspace)
        if sum(path.stat().st_size for path in selected) > 4 * 1024**3:
            raise ValueError("Stage inputs exceed bounded assembly budget")
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED) as archive:
            for path in selected:
                name = str(path.relative_to(workspace))
                # A fresh audit cannot accidentally reuse an earlier report.
                if name.startswith("review/") and slot.startswith("review"):
                    name = "worker-history/previous-audit/" + name
                if name.startswith("previous-run/"):
                    name = "worker-history/" + slot + "/" + name
                archive.write(path, name)
            if native is not None:
                for path in native.rglob("*"):
                    if (
                        path.is_file()
                        and path.stat().st_size < 1024**2
                        and path.suffix in {".json", ".jsonl", ".txt", ".log"}
                    ):
                        archive.write(path, "previous-run/native/" + str(path.relative_to(native)))

    def model(self, slot, workspace=None, native=None):
        directory = self.root / slot
        directory.mkdir(exist_ok=False)
        archive = directory / "inputs.zip"
        if workspace is None:
            shutil.copyfile(self.root / "inputs.zip", archive)
        else:
            self.inputs(workspace, archive, slot, native)
        spec = dict(self.plan["stage_templates"][slot])
        spec["input_zip_sha256"] = file_hash(archive)
        write_json(directory / "run-spec.json", spec)
        for name in ("zcode.cjs", "zcode-builtin.json"):
            shutil.copyfile(self.root / name, directory / name)
        self.upload(archive, slot + "/inputs.zip")
        self.upload(directory / "run-spec.json", slot + "/run-spec.json")
        self.stages.append(
            {
                "slot": slot,
                "status": "started",
                "input_sha256": spec["input_zip_sha256"],
                "prompt_sha256": spec["prompt_sha256"],
                "request_cap": spec["request_cap"],
            }
        )
        self.checkpoint("running")
        author_env = {key: value for key, value in os.environ.items() if key != "DAYTONA_API_KEY"}
        self.command(
            [sys.executable, str(self.root / "zcode_smoke.py")],
            directory,
            spec["wall_seconds"] + 600,
            author_env | {
                "BIOTASKS_ARTIFACT_PREFIX": self.prefix + "/" + slot,
                "BIOTASKS_FACTORY_RUNTIME": str(self.root / "factory-runtime.zip"),
            },
        )
        records = directory / "records"
        result = json.loads((records / "result.json").read_text())
        if len(result["requests"]) > spec["request_cap"]:
            raise ValueError("Observed request count exceeds frozen stage budget")
        # Verify the exported workspace before treating a stage as recoverable.
        manifest = json.loads((records / "artifact-manifest.json").read_text())
        for entry in manifest:
            digest = hashlib.sha256()
            with fsspec.open(
                self.prefix + "/" + slot + "/workspace/" + entry["path"], "rb"
            ).open() as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError("Worker artifact read-back mismatch")
        self.stages[-1].update(
            status=result["outcome"],
            requests=len(result["requests"]),
            elapsed_seconds=result["elapsed_seconds"],
        )
        self.checkpoint("running")
        return directory / "author-workspace", result

    def harbor(self, slot, parent_slot):
        directory = self.root / slot
        directory.mkdir(exist_ok=False)
        parent = self.root / parent_slot / "records"

        def read(name):
            return json.loads((parent / name).read_text())

        source_spec = json.loads((self.root / parent_slot / "run-spec.json").read_text())
        source = {
            "input_sha256": source_spec["input_zip_sha256"],
            "generated_manifest": read("artifact-manifest.json"),
            "deleted_inputs": read("deleted-inputs.json"),
            "task_manifest": read("final-task-manifest.json"),
        }
        bundle = self.root / "harbor-input.zip"
        shutil.copyfile(bundle, directory / bundle.name)
        # Python resolves sibling imports from the script's directory, not cwd.
        # The Harbor bundle extracts its helpers into this stage directory.
        shutil.copyfile(self.root / "harbor_worker.py", directory / "harbor_worker.py")
        spec = {
            "name": slot,
            "stage": "baseline" if slot == "baseline" else "native_suite",
            "development_mode": "factory_only",
            "factory_revision": self.plan["factory_revision"],
            "authoring_sources": [source],
            "expected_task_files": source["task_manifest"],
            "execution_bundle_sha256": file_hash(bundle),
            "native_limits": self.plan["native_limits"],
        }
        write_json(directory / "run-spec.json", spec)
        self.upload(directory / "run-spec.json", slot + "/run-spec.json")
        self.stages.append({"slot": slot, "status": "started"})
        self.checkpoint("running")
        env = os.environ | {
            "BIOTASKS_ARTIFACT_PREFIX": self.prefix + "/" + slot,
            "BIOTASKS_SOURCE_0": self.prefix + "/" + parent_slot,
        }
        seconds = (
            2400
            if slot == "baseline"
            else self.plan["native_limits"]["maximum_trials"] * 2100 + 1200
        )
        self.command([sys.executable, str(directory / "harbor_worker.py")], directory, seconds, env)
        outcome = json.loads((directory / "records/outcome.json").read_text())
        if not outcome.get("orchestration_finished"):
            raise RuntimeError("Harbor worker did not complete; preserve infrastructure outcome")
        self.stages[-1]["status"] = "finished"
        self.checkpoint("running")
        return directory / "records"

    def run(self):
        if (
            self.plan["workflow_version"] != 2
            or file_hash(self.root / "inputs.zip") != self.plan["input_zip_sha256"]
        ):
            raise ValueError("Seed pipeline requires the exact frozen v2 input")
        workspace, result = self.model("specification")
        if result["outcome"] != "worker_finished":
            return self.checkpoint("specification_incomplete")
        action = proposal_action(workspace)
        if action == "rejected":
            return self.checkpoint("rejected", rejection_stage="specification")
        for build_slot, review_slot in (
            ("construction", "review"),
            ("repair", "review_after_repair"),
        ):
            workspace, result = self.model(build_slot, workspace)
            worker = WorkerEvidence(
                build_slot, "succeeded", result["outcome"], True, candidate_hash(workspace)
            )
            decision = decide(worker, None, workspace=workspace)
            if decision.action == "rejected":
                return self.checkpoint("rejected", rejection_stage=build_slot)
            native_records = self.harbor("native_after_" + build_slot, build_slot)
            native_directory = native_records / "native"
            native = NativeEvidence.from_records(workspace, native_directory)
            decision = decide(worker, native, workspace=workspace)
            if decision.action not in {"review", "review_after_repair"}:
                return self.checkpoint(decision.action, reason=decision.reason)
            before = candidate_hash(workspace)
            workspace, result = self.model(review_slot, workspace, native_records)
            integrity = {
                "candidate_unchanged": before == candidate_hash(workspace),
                "candidate_sha256": before,
            }
            write_json(self.root / review_slot / "review-integrity.json", integrity)
            self.upload(
                self.root / review_slot / "review-integrity.json",
                review_slot + "/review-integrity.json",
            )
            report_path = workspace / "review/report.json"
            report = json.loads(report_path.read_text()) if report_path.is_file() else None
            worker = WorkerEvidence(
                review_slot, "succeeded", result["outcome"], True, candidate_hash(workspace)
            )
            decision = decide(
                worker,
                native,
                workspace=workspace,
                review_report=report,
                candidate_unchanged=integrity["candidate_unchanged"],
                reviewed_candidate_sha256=before,
                native_directory=native_directory,
            )
            if decision.action == "repair":
                continue
            if decision.action != "baseline":
                return self.checkpoint(decision.action, reason=decision.reason)
            accepted = acceptance(workspace, native_directory, report, integrity)
            self.accepted = accepted["status"] == "accepted"
            write_json(self.root / "acceptance.json", accepted)
            self.upload(self.root / "acceptance.json", "acceptance.json")
            records = self.harbor("baseline", review_slot)
            paths = list((records / "jobs").glob("*/*/attempts/000/result.json"))
            if len(paths) != 1:
                return self.checkpoint(
                    "accepted", baseline_status="ungraded", reason="Missing unique baseline result"
                )
            trial = json.loads(paths[0].read_text())
            grade_path = paths[0].parent / "verifier/grade.json"
            if not grade_path.is_file():
                return self.checkpoint(
                    "accepted",
                    baseline_status="ungraded",
                    reason="Missing baseline grading evidence",
                )
            grade = json.loads(grade_path.read_text())
            weights = subgoal_weights(
                json.loads((workspace / "task/grading-contract.json").read_text())
            )
            reward = reward_for(grade["subgoals"], weights)
            reported = ((trial.get("verifier_result") or {}).get("rewards") or {}).get("reward")
            if reported != reward or (
                (trial.get("exception_info") or {}).get("exception_type")
                not in {None, "AgentTimeoutError"}
            ):
                return self.checkpoint(
                    "accepted",
                    baseline_status="ungraded",
                    reason="Baseline infrastructure or grading inconsistency",
                )
            return self.checkpoint(
                "accepted",
                baseline_status="graded",
                reward=reward,
                subgoals=grade["subgoals"],
                full_success=all(grade["subgoals"].values()),
            )
        return self.checkpoint("budget_exhausted")


def main():
    pipeline = SeedPipeline(Path.cwd())
    try:
        pipeline.run()
    except Exception as error:
        pipeline.checkpoint(
            "accepted" if pipeline.accepted else "incomplete",
            error_type=type(error).__name__,
            **({"baseline_status": "ungraded"} if pipeline.accepted else {}),
        )
        raise
    finally:
        for stage in pipeline.stages:
            log = pipeline.root / stage["slot"] / "launcher.log"
            if log.is_file():
                value = log.read_text(errors="replace")
                for secret in pipeline.secrets:
                    value = value.replace(secret, "[REDACTED]")
                log.write_text(value)
                pipeline.upload(log, stage["slot"] + "/launcher.log")


if __name__ == "__main__":
    main()
