"""Resume fixed-handle native validation, preservation and exact-worker cleanup."""

import copy
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any

from biotasks.validation import bridge, budget, collection, preservation
from biotasks.validation.archives import verify_package
from biotasks.validation.files import ValidationError, json_sha, read_json, require, sha, write_json
from biotasks.validation.journal import Binding, Observation, advance
from biotasks.validation.planning import code_identity


def bind(path: Path) -> Binding:
    return Binding(str(path), sha(path))


def verify_plan(root: Path) -> dict[str, Any]:
    plan = read_json(root / "plan.json")
    original = copy.deepcopy(plan)
    identity = original.pop("plan_identity")
    for group in original["tasks"]:
        for key in ("run_id", "payload_directory", "payload_sha256"):
            group.pop(key)
    require(json_sha(original) == identity, "Plan identity changed")
    require(
        sha(root / "manifest.snapshot.json") == plan["manifest_sha256"], "Manifest snapshot changed"
    )
    require(
        plan["model_calls_enabled"] is False and plan["new_capacity_allowed"] is False,
        "Unsupported execution policy",
    )
    require(
        code_identity() == plan["code_identity"],
        "Installed validation code changed; use the original environment or a new plan",
    )
    require(
        sha(Path(plan["backend"]["config"])) == plan["backend_config_sha256"],
        "Iris configuration changed",
    )
    for group in plan["tasks"]:
        payload = root / group["payload_directory"]
        require(
            {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
            == set(group["payload_sha256"]),
            "Payload inventory changed",
        )
        for name, digest in group["payload_sha256"].items():
            bind(root / group["payload_directory"] / name).verify()
            require(sha(root / group["payload_directory"] / name) == digest, "Payload changed")
        for key in ("package", "notices"):
            package = group[key]
            require(sha(root / package["path"]) == package["sha256"], "Source package changed")
            verify_package(root / package["path"], package["files"])
    return plan


class Pipeline:
    def __init__(self, root: Path, plan: dict[str, Any], group: dict[str, Any]):
        self.root, self.plan, self.group = root, plan, group
        self.directory = root / "runs" / group["id"]
        self.directory.mkdir(parents=True, exist_ok=True)
        self.backend = plan["backend"]
        self.ledger = Path(plan["budget_ledger"])

    def client(
        self, action: str, group: dict[str, Any], directory: Path, **extra: Any
    ) -> dict[str, Any]:
        # A completed journal performs no transport calls. Before each new
        # remote effect/query, fail closed on an SDK or configuration change.
        profile = bridge.call(
            self.backend, {"action": "fingerprint"}, self.root / "client-profile.current.log"
        )
        require(profile == self.plan["client_profile"], "Iris client profile changed")
        return bridge.call(
            self.backend,
            {
                "action": action,
                "group": group,
                "payload_directory": str(self.root / group["payload_directory"]),
                "payload_sha256": group["payload_sha256"],
                "submission_file": str(directory / "submission.json"),
                **extra,
            },
            directory / (action + ".log"),
        )

    def probe(self, stage: str) -> Observation:
        path = self.directory / (stage + ".json")
        if path.exists():
            return Observation("ready", (bind(path),))
        held = self.directory / "held.json"
        if held.exists() and read_json(held).get("stop_verified"):
            return Observation("held", reason=read_json(held)["reason"])
        return Observation("absent")

    def verify(self, stage: str, evidence: tuple[Binding, ...]) -> None:
        require(
            len(evidence) == 1 and Path(evidence[0].path) == self.directory / (stage + ".json"),
            "Unexpected stage evidence",
        )
        value = read_json(Path(evidence[0].path))
        require(
            value["run_id"] == self.group["run_id"] and value["stage"] == stage,
            "Stage identity changed",
        )
        for item in value["bindings"]:
            Binding(**item).verify()
        if stage == "candidate_verified":
            require(value["admission"]["admitted_before_submission"], "Missing admission")
        elif stage == "archive_readback_verified":
            require(value["readback"]["durable_readback_verified"], "Missing archive readback")
        elif stage == "publication_resolved":
            preservation.verify_receipt(self.directory)
        elif stage == "cleanup_verified":
            require(
                value["cleanup"]["verified_empty"] or value["cleanup"].get("verified_no_creation"),
                "Cleanup incomplete",
            )
            preservation.verify_receipt(self.directory / "cleanup")

    def record(self, stage: str, paths: list[Path], **value: Any) -> None:
        write_json(
            self.directory / (stage + ".json"),
            {
                "run_id": self.group["run_id"],
                "stage": stage,
                "bindings": [bind(p).json() for p in paths],
                **value,
            },
        )

    def perform(self, stage: str) -> None:
        {
            "candidate_verified": self.candidate,
            "submission_recorded": self.submission,
            "remote_terminal": self.terminal,
            "archive_readback_verified": self.archive,
            "publication_resolved": self.publish,
            "cleanup_terminal": self.cleanup,
            "cleanup_verified": self.cleanup_verified,
        }[stage]()

    def recover(self, stage: str) -> None:
        # Every implementation inspects its durable sub-intent first. Transport
        # submission writes its own locked intent before RPC; an uncertain RPC
        # can only observe its original handle, never submit another identity.
        self.perform(stage)

    def candidate(self) -> None:
        preflight = self.client("preflight", self.group, self.directory)
        admission = budget.admit(
            self.ledger,
            self.group["run_id"],
            self.group["resources"]["maximum_cpu_hours"],
            self.group["resources"]["cleanup_cpu_hours"],
        )
        self.record("candidate_verified", [], preflight=preflight, admission=admission)

    def ensure_submission(
        self, group: dict[str, Any], directory: Path, **extra: Any
    ) -> dict[str, Any] | None:
        file = directory / "submission.json"
        directory.mkdir(parents=True, exist_ok=True)
        if not file.exists():
            budget.verify_reserved(self.ledger, group["run_id"])
            self.client("submit", group, directory, **extra)
        receipt = read_json(file)
        require(
            receipt["job_id"] == "/exedev/" + group["run_id"]
            and receipt["payload_sha256"] == group["payload_sha256"],
            "Submission identity changed",
        )
        if receipt["state"] == "submission_pending":
            observed = self.client("observe", group, directory)
            if observed["state"] == "handle_missing":
                return None
        return receipt

    def submission(self) -> None:
        receipt = self.ensure_submission(self.group, self.directory)
        if receipt is not None:
            self.record(
                "submission_recorded",
                [self.directory / "submission.json"],
                job_id=receipt["job_id"],
            )

    def observe(self, group: dict[str, Any], directory: Path) -> dict[str, Any] | None:
        file = directory / "accounting.json"
        if not file.exists():
            observed = self.client("observe", group, directory)
            write_json(directory / "observation.json", observed)
            if not observed.get("terminal"):
                return None
            write_json(file, observed)
        value = read_json(file)
        require(
            value["terminal"] and value["job_id"] == "/exedev/" + group["run_id"],
            "Wrong accounting handle",
        )
        budget.reconcile(self.ledger, group["run_id"], value["allocated_cpu_hours"])
        return value

    def terminal(self) -> None:
        if self.observe(self.group, self.directory) is not None:
            self.record("remote_terminal", [self.directory / "accounting.json"])

    def auxiliary(self, role: str, **settings: Any) -> tuple[dict[str, Any], Path, dict[str, Any]]:
        primary = read_json(self.directory / "submission.json")
        directory = self.directory / role
        group_file = directory / "group.json"
        group = copy.deepcopy(self.group)
        group["run_id"] += "-" + role
        group["resources"] = {"cpus": 2, "memory_gib": 4, "disk_gib": 4, "timeout_seconds": 270}
        payload = directory / "payload"
        if not group_file.exists():
            require(
                not (directory / "submission.json").exists(),
                "Auxiliary identity missing after submission",
            )
            if payload.exists():
                shutil.rmtree(payload)
            shutil.copytree(self.root / self.group["payload_directory"], payload)
            config = read_json(payload / "family.json")
            config.update(
                operation=role,
                resources=group["resources"],
                target_worker_id=primary["worker_id"],
                **settings,
            )
            write_json(payload / "family.json", config)
            hashes = {
                p.relative_to(payload).as_posix(): sha(p)
                for p in payload.rglob("*")
                if p.is_file() and p.name != "payload.json"
            }
            write_json(payload / "payload.json", {"run_id": self.group["run_id"], "sha256": hashes})
            group["payload_directory"] = payload.relative_to(self.root).as_posix()
            group["payload_sha256"] = {
                p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
            }
            write_json(group_file, group)
        else:
            group = read_json(group_file)
            config = read_json(payload / "family.json")
            require(
                all(config.get(k) == v for k, v in settings.items()), "Auxiliary parameters changed"
            )
        for name, digest in group["payload_sha256"].items():
            require(sha(payload / name) == digest, "Auxiliary payload changed")
        return (
            group,
            directory,
            {
                "target": {
                    "worker_id": primary["worker_id"],
                    "worker_tpu_name": primary["worker_tpu_name"],
                },
                "primary_run_id": self.group["run_id"],
            },
        )

    def stop_and_hold(self, reason: str) -> None:
        group, directory, extra = self.auxiliary("stop")
        if self.ensure_submission(group, directory, **extra) is None:
            return
        account = self.observe(group, directory)
        if account is None:
            return
        raw = collection.download(account, directory, self.backend.get("gcloud", "gcloud"))
        report, _ = collection.envelope(
            raw,
            read_json(directory / "submission.json"),
            group["payload_sha256"],
            "stop",
            self.group["run_id"],
        )
        require(
            report.get("stop", {}).get("verified_stopped") is True,
            "Emergency stop unverified; retain all evidence",
        )
        write_json(
            self.directory / "held.json",
            {
                "reason": reason,
                "stop_verified": True,
                "stop_report_sha256": sha(raw),
                "remote_data_retained": True,
                "operator_action": "Salvage the retained volume; do not regenerate, delete or assume empty output means no creation",
            },
        )

    def archive(self) -> None:
        account = read_json(self.directory / "accounting.json")
        sources = [self.directory / "accounting.json", self.directory / "submission.json"]
        if account.get("verified_no_creation"):
            require(account["attempts"] == 0, "Invalid scheduler no-creation proof")
            result = {
                "stage": "scheduler_not_started",
                "verified_no_creation": True,
                "positive_control_pair": False,
                "clean_oracle_command": False,
                "durable_readback_verified": True,
            }
        else:
            try:
                raw = collection.download(
                    account, self.directory, self.backend.get("gcloud", "gcloud")
                )
                report, outer = collection.envelope(
                    raw,
                    read_json(self.directory / "submission.json"),
                    self.group["payload_sha256"],
                    "execute",
                    self.group["run_id"],
                )
                result = collection.classify(self.group, report, outer)
                require(result["verified_stopped"], "Execution stop not verified")
                require(
                    result["verified_no_creation"] or result["control_archive_sha256"],
                    "No retained-volume evidence seal; preserve for salvage",
                )
                result["durable_readback_verified"] = True
                sources.append(raw)
            except (
                ValidationError,
                KeyError,
                ValueError,
                OSError,
                subprocess.SubprocessError,
                tarfile.TarError,
            ) as error:
                self.stop_and_hold(str(error))
                return
        write_json(self.directory / "readback.json", result)
        sources.append(self.directory / "readback.json")
        self.record("archive_readback_verified", sources, readback=result)

    def publication_sources(self, directory: Path, extra: dict[str, Path]) -> dict[str, Path]:
        sources = {
            "source/tasks.tar.gz": self.root / self.group["package"]["path"],
            "source/notices.tar.gz": self.root / self.group["notices"]["path"],
            **extra,
        }
        for name in ("submission.json", "accounting.json", "readback.json", "runtime.tar.zst"):
            if (directory / name).exists():
                sources["execution/" + name] = directory / name
        return sources

    def publish(self) -> None:
        metadata = {
            "run_id": self.group["run_id"],
            "repo2rlenv_revision": self.plan["repo2rlenv_revision"],
            "validation_code_identity": self.plan["code_identity"],
            "task": self.group["task"],
            "publication_policy": self.group["publication"],
            "new_capacity": False,
            "model_calls": 0,
        }
        preservation.prepare(self.directory, self.publication_sources(self.directory, {}), metadata)
        preservation.publish(self.directory, self.plan["archive"], self.group["publication"])
        self.record(
            "publication_resolved",
            [self.directory / "preserved/manifest.json", self.directory / "publication.json"],
        )

    def cleanup(self) -> None:
        readback = read_json(self.directory / "readback.json")
        if readback["verified_no_creation"]:
            proof = {
                "verified_empty": True,
                "verified_no_creation": True,
                "reason": "Source-bound or zero-attempt scheduler proof",
            }
            budget.release_cleanup(self.ledger, self.group["run_id"], proof)
            budget.release_cleanup(self.ledger, self.group["run_id"], proof, "stop")
            write_json(self.directory / "cleanup-proof.json", proof)
            self.record("cleanup_terminal", [self.directory / "cleanup-proof.json"])
            return
        preservation.verify_receipt(self.directory)
        group, directory, extra = self.auxiliary(
            "cleanup",
            archival_verified=True,
            control_archive_sha256=readback["control_archive_sha256"],
            protected_base=readback["protected_base"],
        )
        if self.ensure_submission(group, directory, **extra) is None:
            return
        account = self.observe(group, directory)
        if account is None:
            return
        raw = collection.download(account, directory, self.backend.get("gcloud", "gcloud"))
        report, _ = collection.envelope(
            raw,
            read_json(directory / "submission.json"),
            group["payload_sha256"],
            "cleanup",
            self.group["run_id"],
        )
        proof = report.get("cleanup", {})
        require(
            proof.get("verified_empty") is True and not any(proof["remaining"].values()),
            "Cleanup incomplete; preserve all evidence, never resubmit",
        )
        write_json(self.directory / "cleanup-proof.json", proof)
        budget.release_cleanup(self.ledger, self.group["run_id"], proof, "stop")
        self.record(
            "cleanup_terminal",
            [
                raw,
                directory / "accounting.json",
                directory / "submission.json",
                self.directory / "cleanup-proof.json",
            ],
        )

    def cleanup_verified(self) -> None:
        directory = self.directory / "cleanup"
        directory.mkdir(exist_ok=True)
        sources = self.publication_sources(
            directory,
            {
                "cleanup-proof.json": self.directory / "cleanup-proof.json",
                "primary-manifest.json": self.directory / "preserved/manifest.json",
                "primary-publication.json": self.directory / "publication.json",
            },
        )
        preservation.prepare(
            directory,
            sources,
            {"run_id": self.group["run_id"], "operation": "cleanup", "model_calls": 0},
        )
        preservation.publish(directory, self.plan["archive"], self.group["publication"])
        self.record(
            "cleanup_verified",
            [
                self.directory / "cleanup-proof.json",
                directory / "preserved/manifest.json",
                directory / "publication.json",
            ],
            cleanup=read_json(self.directory / "cleanup-proof.json"),
        )

    def step(self) -> str:
        inputs = (bind(self.root / "plan.json"),)
        return advance(self.group["run_id"], inputs, self.directory / "journal.json", self)


def run(root: Path, once: bool = False) -> dict[str, Any]:
    root = root.resolve()
    plan = verify_plan(root)
    states: dict[str, str] = {}
    for group in plan["tasks"]:
        pipeline = Pipeline(root, plan, group)
        while True:
            state = pipeline.step()
            states[group["id"]] = state
            if state == "complete":
                break
            if state.startswith("held:"):
                return {"state": "held", "tasks": states, "unsupported": plan["unsupported"]}
            if once:
                return {"state": "in_progress", "tasks": states, "unsupported": plan["unsupported"]}
            if state.startswith(
                (
                    "pending:",
                    "recovering:submission_recorded",
                    "recovering:remote_terminal",
                    "recovering:archive_readback_verified",
                    "recovering:cleanup_terminal",
                )
            ):
                time.sleep(300)
    return {
        "state": "complete" if plan["tasks"] else "unsupported",
        "tasks": states,
        "unsupported": plan["unsupported"],
    }


def status(root: Path) -> dict[str, Any]:
    plan = verify_plan(root.resolve())
    return {
        "plan_identity": plan["plan_identity"],
        "unsupported": plan["unsupported"],
        "tasks": [
            {
                "id": g["id"],
                "repo": g["repo"],
                "journal": read_json(root / "runs" / g["id"] / "journal.json")
                if (root / "runs" / g["id"] / "journal.json").exists()
                else None,
            }
            for g in plan["tasks"]
        ],
    }
