"""Generation adapter to the already tested fixed-handle validation lifecycle."""

import json
import os
import shutil
import subprocess
import tarfile
import tomllib
from decimal import Decimal

import generation_bridge
import model_budget
from biotasks.validation import bridge, budget, collection, preservation
from biotasks.validation.archives import records
from biotasks.validation.controller import Pipeline
from biotasks.validation.files import ValidationError, read_json, require, safe, sha, write_json
from generation_publication import text_observations


def billing(phase, report):
    if not report.get("generation_started"):
        return {
            "known_actual_usd": "0",
            "calls": 0,
            "complete": True,
            "reason": "Source-bound worker never invoked native generation",
        }
    target = phase.get("native-observations/billing.json")
    events = phase.get("native-observations/events.jsonl")
    if not target:
        return {
            "known_actual_usd": "0",
            "calls": None,
            "complete": False,
            "reason": "Attempted generation without final billing evidence",
        }
    value = json.loads(target["data"])
    rows = [json.loads(line) for line in events["data"].splitlines()] if events else []
    requests = [r["call"] for r in rows if r["event"] == "model_request"]
    charges = [r for r in rows if r["event"] == "model_charge"]
    require(
        requests == list(range(1, len(requests) + 1)) and len(requests) <= 20,
        "Unexpected original model request identities",
    )
    require(
        len({r["call"] for r in charges}) == len(charges)
        and all(r["call"] in requests for r in charges),
        "Duplicate or unknown model charge",
    )
    known = sum(
        (
            model_budget.amount(r["actual_cost_usd"])
            for r in charges
            if r["actual_cost_usd"] is not None
        ),
        Decimal(0),
    )
    require(
        known == model_budget.amount(value["actual_cost_usd"]),
        "Billing aggregate differs from original events",
    )
    require(isinstance(value["cost_complete"], bool), "Invalid cost completeness flag")
    complete = (
        bool(value["cost_complete"])
        and len(charges) == len(requests)
        and all(r["actual_cost_usd"] is not None for r in charges)
    )
    require(value["model_calls"] == len(requests), "Recorded model count differs")
    return {
        "known_actual_usd": str(known),
        "calls": len(requests),
        "complete": complete,
        "reason": "Original upstream observed request/charge events",
    }


class GenerationPipeline(Pipeline):
    def client(self, action, group, directory, **extra):
        if group["run_id"] != self.group["run_id"]:
            return super().client(action, group, directory, **extra)
        profile = bridge.call(
            self.backend, {"action": "fingerprint"}, self.root / "client-profile.current.log"
        )
        require(profile == self.plan["client_profile"], "SDK profile changed")
        return generation_bridge.call(
            self.backend,
            {
                "action": action,
                "group": group,
                "payload_directory": str(self.root / group["payload_directory"]),
                "payload_sha256": group["payload_sha256"],
                "submission_file": str(directory / "submission.json"),
                "model_ledger": str(self.ledger),
                "plan_identity": self.plan["plan_identity"],
                **extra,
            },
            directory / (action + ".log"),
        )

    def candidate(self):
        preflight = self.client("preflight", self.group, self.directory)
        existing = next(
            (
                e
                for e in read_json(self.ledger)["events"]
                if e.get("run_id") == self.group["run_id"] and e["kind"] == "reserved_cpu_admission"
            ),
            None,
        )
        if existing:
            budget.verify_reserved(self.ledger, self.group["run_id"])
            admission = {
                "admitted_before_submission": True,
                "run_id": self.group["run_id"],
                "maximum_cpu_hours": existing["maximum_allocated_cpu_hours"],
            }
        else:
            admission = budget.admit(
                self.ledger,
                self.group["run_id"],
                self.group["resources"]["maximum_cpu_hours"],
                self.group["resources"]["cleanup_cpu_hours"],
            )
        model = model_budget.reserve(
            self.ledger,
            self.group["run_id"],
            self.plan["model_budget"]["maximum_usd"],
            self.plan["model_budget"]["quote_sha256"],
            self.plan["plan_identity"],
        )
        model_budget.verify_reserved(self.ledger, self.group["run_id"], self.plan["plan_identity"])
        write_json(self.directory / "model-admission.json", model)
        admission.pop("model_calls", None)
        self.record(
            "candidate_verified",
            [self.directory / "model-admission.json"],
            preflight=preflight,
            admission=admission,
        )

    def reconcile_model(self, value, proof):
        try:
            row = model_budget.reconcile(
                self.ledger,
                self.group["run_id"],
                value["known_actual_usd"],
                value["calls"],
                value["complete"],
                sha(proof),
            )
            write_json(self.directory / "model-accounting.json", row)
        except model_budget.ModelBudgetExceeded as error:
            write_json(
                self.directory / "model-budget-hold.json",
                {
                    "reason": str(error),
                    "actual_recorded": True,
                    "preservation_and_reserved_cleanup_allowed": True,
                },
            )

    def archive(self):
        account = read_json(self.directory / "accounting.json")
        paths = [self.directory / "accounting.json", self.directory / "submission.json"]
        if account.get("verified_no_creation"):
            require(account["attempts"] == 0, "Invalid zero-attempt proof")
            result = {
                "stage": "scheduler_not_started",
                "verified_no_creation": True,
                "durable_readback_verified": True,
                "model_billing": {
                    "known_actual_usd": "0",
                    "calls": 0,
                    "complete": True,
                    "reason": "Terminal scheduler zero-attempt proof",
                },
                "exported_tasks": [],
            }
            self.reconcile_model(result["model_billing"], self.directory / "accounting.json")
        else:
            try:
                raw = collection.download(
                    account, self.directory, self.backend.get("gcloud", "gcloud")
                )
                report, outer = collection.envelope(
                    raw,
                    read_json(self.directory / "submission.json"),
                    self.group["payload_sha256"],
                    "generate",
                    self.group["run_id"],
                )
                no_creation = bool(report.get("cleanup", {}).get("verified_no_creation"))
                require(
                    no_creation or report.get("stop", {}).get("verified_stopped"),
                    "Generation execution is not stopped",
                )
                phase = (
                    records(outer["control-artifacts.tar.gz"]["data"], "tar.gz")
                    if "control-artifacts.tar.gz" in outer
                    else {}
                )
                require(
                    no_creation or bool(phase) or "control-artifacts.tar.gz" in outer,
                    "No source-bound retained archive",
                )
                destination = self.directory / "generation-source"
                if not destination.exists():
                    stage = self.directory / "generation-source-staging"
                    if stage.exists():
                        require(
                            stage.is_dir() and not stage.is_symlink(), "Unsafe extraction staging"
                        )
                        shutil.rmtree(stage)
                    stage.mkdir()
                    for name, row in phase.items():
                        target = stage / safe(name)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(row["data"])
                        target.chmod(row["mode"])
                        with target.open("rb") as stream:
                            os.fsync(stream.fileno())
                    for folder in [
                        *sorted(
                            (p for p in stage.rglob("*") if p.is_dir()),
                            key=lambda p: len(p.parts),
                            reverse=True,
                        ),
                        stage,
                    ]:
                        descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
                        try:
                            os.fsync(descriptor)
                        finally:
                            os.close(descriptor)
                    stage.rename(destination)
                    descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                # Validate any existing extraction against every source byte.
                require(
                    {
                        p.relative_to(destination).as_posix()
                        for p in destination.rglob("*")
                        if p.is_file()
                    }
                    == set(phase),
                    "Unexpected extracted generation members",
                )
                for name, row in phase.items():
                    target = destination / safe(name)
                    require(
                        target.is_file()
                        and sha(target) == row["sha256"]
                        and target.stat().st_mode & 0o777 == row["mode"],
                        "Extracted generation source changed",
                    )
                exported = []
                expected = read_json(self.root / "reference-candidates.json")
                for name, row in phase.items():
                    if name.startswith("outputs/raw/") and name.endswith("/task.toml"):
                        metadata = tomllib.loads(row["data"].decode())["metadata"]["repo2env"]
                        require(
                            metadata["pipeline"] == "pr_runtime"
                            and metadata["repo"] == expected["repo"],
                            "Unexpected exported repository/pipeline",
                        )
                        require(
                            metadata["pr_runtime"]["base_commit"]
                            in {r["base_sha"] for r in expected["candidates"]},
                            "Exported base differs from frozen listing",
                        )
                        exported.append(
                            name.removeprefix("outputs/raw/").removesuffix("/task.toml")
                        )
                require(
                    len(exported) <= len(expected["candidates"]),
                    "More exports than frozen candidates",
                )
                billed = billing(phase, report)
                result = {
                    "stage": report["stage"],
                    "verified_no_creation": no_creation,
                    "verified_stopped": True,
                    "control_archive_sha256": outer.get("control-artifacts.tar.gz", {}).get(
                        "sha256"
                    ),
                    "protected_base": report.get("protected_base"),
                    "durable_readback_verified": True,
                    "model_billing": billed,
                    "exported_tasks": sorted(exported),
                    "native_exit": report.get("native_exit"),
                    "generation_started": report.get("generation_started"),
                    "task_repairs": 0,
                    "source_members": [
                        {
                            "path": name,
                            "bytes": row["bytes"],
                            "mode": row["mode"],
                            "sha256": row["sha256"],
                        }
                        for name, row in sorted(phase.items())
                    ],
                }
                self.reconcile_model(billed, raw)
                paths.append(raw)
            except (
                ValidationError,
                KeyError,
                ValueError,
                OSError,
                subprocess.SubprocessError,
                tarfile.TarError,
            ) as error:
                entry = next(
                    e
                    for e in model_budget.rows(read_json(self.ledger))
                    if e["run_id"] == self.group["run_id"]
                )
                if entry["state"] != "terminal reconciled":
                    self.reconcile_model(
                        {
                            "known_actual_usd": entry["known_actual_usd"],
                            "calls": None,
                            "complete": False,
                        },
                        self.directory / "accounting.json",
                    )
                self.stop_and_hold(type(error).__name__ + ": " + str(error)[:200])
                return
        write_json(self.directory / "readback.json", result)
        paths.append(self.directory / "readback.json")
        if (self.directory / "model-accounting.json").exists():
            paths.append(self.directory / "model-accounting.json")
        self.record("archive_readback_verified", paths, readback=result)

    def publication_sources(self, directory, extra):
        sources = {
            "source/native-config.json": self.root / "native-config.json",
            "source/reference-candidates.json": self.root / "reference-candidates.json",
            "source/notices.tar.gz": self.root / self.group["notices"]["path"],
            "source/plan.json": self.root / "plan.json",
            **extra,
        }
        for name in (
            "submission.json",
            "accounting.json",
            "readback.json",
            "runtime.tar.zst",
            "model-accounting.json",
            "model-budget-hold.json",
            "budget-hold.json",
        ):
            if (directory / name).exists():
                sources["execution/" + name] = directory / name
        return sources

    def publish(self):
        value = read_json(self.directory / "readback.json")
        preservation.prepare(
            self.directory,
            self.publication_sources(self.directory, {}),
            {
                "run_id": self.group["run_id"],
                "operation": "official_generation",
                "upstream_revision": self.plan["repo2rlenv_revision"],
                "model_billing": value["model_billing"],
                "exported_tasks": value["exported_tasks"],
                "task_repairs": 0,
                "publication_policy": self.group["publication"],
            },
        )
        with text_observations():
            preservation.publish(self.directory, self.plan["archive"], self.group["publication"])
        self.record(
            "publication_resolved",
            [self.directory / "preserved/manifest.json", self.directory / "publication.json"],
        )

    def cleanup_verified(self):
        with text_observations():
            return super().cleanup_verified()
