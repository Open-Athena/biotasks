"""Automatic source-bound retention of supported unaccepted native controls.

Operator inputs are a frozen validation root and a separate retention root, not
task identifiers or log hashes. This actor never drives a primary/stop job,
rewrites the original journal, accepts scores or relaxes budget admission.
"""

import copy
from pathlib import Path

from biotasks.retention import evidence, log_policy
from biotasks.validation import budget, collection, controller, preservation
from biotasks.validation.files import json_sha, lock, read_json, require, safe, sha, write_json
from biotasks.validation.journal import Binding, Observation, advance

ROOT = Path(__file__).resolve().parent
CODE = ("actor.py", "evidence.py", "log_policy.py")
STAGES = (
    "source_verified",
    "archive_preserved",
    "publication_resolved",
    "cleanup_terminal",
    "cleanup_verified",
)


def implementation():
    return {name: sha(ROOT / name) for name in CODE}


def prepare(original, output, prefix=None):
    original, output = original.resolve(), output.resolve()
    require(
        not output.is_relative_to(original) and not original.is_relative_to(output),
        "Retention output overlaps original data",
    )
    plan = controller.verify_plan(original)
    archive = copy.deepcopy(plan["archive"])
    if prefix is not None:
        require(archive["kind"] == "hf-public", "Prefix requires original public-HF policy")
        archive["prefix"] = safe(prefix)
    value = {
        "schema_version": 1,
        "original_root": str(original),
        "original_plan_sha256": sha(original / "plan.json"),
        "original_plan_identity": plan["plan_identity"],
        "task_ids": [group["id"] for group in plan["tasks"]],
        "implementation_sha256": implementation(),
        "archive": archive,
        "native_validation_or_model_calls": False,
        "new_capacity": False,
    }
    value["plan_identity"] = json_sha(value)
    if output.exists():
        require(read_json(output / "plan.json") == value, "Retention plan changed")
    else:
        output.mkdir(parents=True, mode=0o700)
        write_json(output / "plan.json", value)
    return value


def verify(output):
    value = read_json(output / "plan.json")
    old = dict(value)
    require(old.pop("plan_identity") == json_sha(old), "Retention plan identity changed")
    require(value["implementation_sha256"] == implementation(), "Retention implementation changed")
    original = Path(value["original_root"])
    require(sha(original / "plan.json") == value["original_plan_sha256"], "Original plan changed")
    plan = controller.verify_plan(original)
    require(
        value["original_plan_identity"] == plan["plan_identity"]
        and value["task_ids"] == [group["id"] for group in plan["tasks"]],
        "Retention task selection changed",
    )
    archive = dict(value["archive"])
    if archive["kind"] == "hf-public":
        archive["prefix"] = plan["archive"]["prefix"]
    require(archive == plan["archive"], "Retention broadened original publication backend")
    return value, plan


class Retention:
    def __init__(self, output, plan, task_id, *, publish=False, cleanup=False):
        self.output, self.plan = output, plan
        self.pipe, self.source = evidence.verify(Path(plan["original_root"]), task_id)
        self.directory = output / "cases" / safe(task_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.publish_allowed, self.cleanup_allowed = publish, cleanup
        binding = {"retention_plan_identity": plan["plan_identity"], "source": self.source}
        path = self.directory / "input.json"
        if path.exists():
            require(read_json(path) == binding, "Original held source changed")
        else:
            require(not any(self.directory.iterdir()), "Unowned retention case directory")
            write_json(path, binding)

    def policy(self):
        return {
            **self.pipe.group["publication"],
            "review": self.pipe.group["publication"].get("review", "")
            + " Source-bound unaccepted native failure. Automatically derived task/agent/trial-bound UTF-8 verifier text views are inspected without NUL padding; original archive bytes remain unchanged. No grading repair or acceptance.",
        }

    def remote_publication(self):
        return self.plan["archive"]["kind"] == "hf-public" and self.policy()["eligible"]

    def probe(self, stage):
        path = self.directory / (stage + ".json")
        if path.exists():
            return Observation("ready", (Binding(str(path), sha(path)),))
        receipt_dir = self.directory / "cleanup" if stage == "cleanup_verified" else self.directory
        if (
            stage in ("publication_resolved", "cleanup_verified")
            and self.remote_publication()
            and not self.publish_allowed
            and not (receipt_dir / "publication.json").exists()
        ):
            return Observation("pending", reason="public transfer not admitted")
        cleanup_dir = self.pipe.directory / "cleanup"
        if (
            stage == "cleanup_terminal"
            and not self.cleanup_allowed
            and not all(
                (cleanup_dir / name).is_file()
                for name in ("submission.json", "accounting.json", "runtime.tar.zst")
            )
        ):
            return Observation("pending", reason="original cleanup operation not admitted")
        return Observation("absent")

    def verify(self, stage, bindings):
        path = self.directory / (stage + ".json")
        require(
            len(bindings) == 1 and Path(bindings[0].path) == path, "Wrong retention stage evidence"
        )
        value = read_json(path)
        require(
            value["stage"] == stage
            and value["run_id"] == self.pipe.group["run_id"]
            and value["scientific_acceptance"] is False,
            "Retention stage identity/acceptance changed",
        )
        for row in value["bindings"]:
            Binding(**row).verify()
        if stage in ("archive_preserved", "publication_resolved"):
            preservation.verify(self.directory)
        if stage == "publication_resolved":
            preservation.verify_receipt(self.directory)
        if stage in ("cleanup_terminal", "cleanup_verified"):
            self.verify_cleanup(read_json(self.directory / "cleanup-proof.json"))
        if stage == "cleanup_verified":
            preservation.verify_receipt(self.directory / "cleanup")

    def record(self, stage, paths):
        write_json(
            self.directory / (stage + ".json"),
            {
                "stage": stage,
                "run_id": self.pipe.group["run_id"],
                "scientific_acceptance": False,
                "bindings": [{"path": str(path), "sha256": sha(path)} for path in paths],
            },
        )

    def source_verified(self):
        write_json(self.directory / "source.json", self.source)
        self.record(
            "source_verified", [self.directory / "input.json", self.directory / "source.json"]
        )

    def archive_preserved(self):
        pipe = self.pipe
        sources = pipe.publication_sources(
            pipe.directory,
            {
                "original/journal.json": pipe.directory / "journal.json",
                "original/held.json": pipe.directory / "held.json",
                "source/plan.json": pipe.root / "plan.json",
                "retention/input.json": self.directory / "input.json",
                "retention/source.json": self.directory / "source.json",
                "stop/runtime.tar.zst": pipe.directory / "stop/runtime.tar.zst",
                "stop/submission.json": pipe.directory / "stop/submission.json",
                "stop/accounting.json": pipe.directory / "stop/accounting.json",
            },
        )
        preservation.prepare(
            self.directory,
            sources,
            {
                "operation": "automatic held-native retention",
                "run_id": pipe.group["run_id"],
                "scientific_acceptance": False,
                "native_reward_accepted": False,
                "original_journal_remains_held": True,
                "control_archive_sha256": self.source["control_archive_sha256"],
                "protected_base": self.source["protected_base"],
                "inspection_policy": log_policy.POLICY,
                "publication_policy": self.policy(),
            },
        )
        with log_policy.inspection(self.source["inspection_views"]):
            manifest = preservation.verify(self.directory)
            for row in manifest["files"]:
                preservation.inspect(
                    (self.directory / "preserved/files" / row["path"]).read_bytes(), row["path"]
                )
        self.record("archive_preserved", [self.directory / "preserved/manifest.json"])

    def publication_resolved(self):
        if (self.directory / "publication.json").exists():
            preservation.verify_receipt(self.directory)
        else:
            with log_policy.inspection(self.source["inspection_views"]):
                preservation.publish(self.directory, self.plan["archive"], self.policy())
        preservation.verify_receipt(self.directory)
        self.record(
            "publication_resolved",
            [self.directory / "publication.json", self.directory / "preserved/manifest.json"],
        )

    def cleanup_settings(self):
        return {
            "archival_verified": True,
            "control_archive_sha256": self.source["control_archive_sha256"],
            "protected_base": self.source["protected_base"],
        }

    def verify_cleanup(self, proof):
        require(
            proof["run_id"] == self.pipe.group["run_id"]
            and proof["verified_empty"] is True
            and set(proof["remaining"]) == {"containers", "controllers", "images", "volumes"}
            and not any(proof["remaining"].values()),
            "Owned cleanup not verified empty",
        )
        base = proof["protected_public_base"]
        expected = self.source["protected_base"]
        require(
            base["ref"] == expected["ref"] and isinstance(base["present_before"], bool),
            "Wrong protected public base",
        )
        if base["present_before"]:
            require(
                base["preserved"] is True and base["image_id_after"] == expected["image_id"],
                "Public base was not preserved",
            )
        else:
            require(
                base["preserved"] is False and base["image_id_after"] is None,
                "Contradictory absent public base",
            )

    def cleanup_terminal(self):
        preservation.verify_receipt(self.directory)
        pipe = self.pipe
        directory = pipe.directory / "cleanup"
        cached = all(
            (directory / name).is_file()
            for name in ("submission.json", "accounting.json", "runtime.tar.zst")
        )
        intent = {
            "operation": "original pre-reserved exact-worker cleanup only",
            "run_id": pipe.group["run_id"],
            "source_identity": self.source["source_identity"],
            "original_journal_sha256": self.source["original_files_sha256"]["journal.json"],
            "primary_manifest_sha256": sha(self.directory / "preserved/manifest.json"),
            "primary_publication_sha256": sha(self.directory / "publication.json"),
            "settings": self.cleanup_settings(),
        }
        path = self.directory / "cleanup-intent.json"
        if path.exists():
            require(read_json(path) == intent, "Retention cleanup intent changed")
        else:
            write_json(path, intent)
        if not cached:
            require(self.cleanup_allowed, "Cleanup not admitted")
            group, directory, extra = pipe.auxiliary("cleanup", **self.cleanup_settings())
            evidence.auxiliary_contract(pipe, "cleanup", **self.cleanup_settings())
            if (directory / "accounting.json").exists():
                account = read_json(directory / "accounting.json")
                require(
                    account["terminal"] is True
                    and account["job_id"] == "/exedev/" + group["run_id"],
                    "Unknown cached cleanup accounting",
                )
            else:
                if pipe.ensure_submission(group, directory, **extra) is None:
                    return
                account = pipe.observe(group, directory)
                if account is None:
                    return
            collection.download(account, directory, pipe.backend.get("gcloud", "gcloud"))
        group, directory, account, report = evidence.auxiliary(
            pipe, "cleanup", **self.cleanup_settings()
        )
        proof = report["cleanup"]
        self.verify_cleanup(proof)
        ledger = read_json(pipe.ledger)
        entry = next(
            row
            for row in ledger["events"]
            if row.get("kind") == "reserved_cpu_admission" and row.get("run_id") == group["run_id"]
        )
        if entry["state"] != "terminal reconciled":
            try:
                budget.reconcile(pipe.ledger, group["run_id"], account["allocated_cpu_hours"])
            except budget.BudgetExceeded as error:
                write_json(
                    self.directory / "budget-hold.json",
                    {"reason": str(error), "admission_remains_closed": True},
                )
        evidence.reconciled(pipe, "cleanup", account)
        require(
            sha(pipe.directory / "journal.json") == intent["original_journal_sha256"],
            "Original held journal changed",
        )
        write_json(self.directory / "cleanup-proof.json", proof)
        self.record(
            "cleanup_terminal",
            [
                path,
                self.directory / "cleanup-proof.json",
                directory / "runtime.tar.zst",
                directory / "submission.json",
                directory / "accounting.json",
            ],
        )

    def cleanup_verified(self):
        directory = self.directory / "cleanup"
        directory.mkdir(exist_ok=True)
        original = self.pipe.directory / "cleanup"
        sources = self.pipe.publication_sources(
            original,
            {
                "cleanup-proof.json": self.directory / "cleanup-proof.json",
                "retention/cleanup-intent.json": self.directory / "cleanup-intent.json",
                "original/held-journal.json": self.pipe.directory / "journal.json",
                "primary-manifest.json": self.directory / "preserved/manifest.json",
                "primary-publication.json": self.directory / "publication.json",
            },
        )
        preservation.prepare(
            directory,
            sources,
            {
                "operation": "automatic held-native cleanup readback",
                "run_id": self.pipe.group["run_id"],
                "scientific_acceptance": False,
                "native_reward_accepted": False,
            },
        )
        if (directory / "publication.json").exists():
            preservation.verify_receipt(directory)
        else:
            preservation.publish(directory, self.plan["archive"], self.policy())
        preservation.verify_receipt(directory)
        self.record(
            "cleanup_verified",
            [
                directory / "publication.json",
                directory / "preserved/manifest.json",
                self.directory / "cleanup-proof.json",
            ],
        )

    def perform(self, stage):
        getattr(self, stage)()

    def recover(self, stage):
        self.perform(stage)

    def step(self):
        return advance(
            self.pipe.group["run_id"],
            (
                Binding(str(self.output / "plan.json"), sha(self.output / "plan.json")),
                Binding(str(self.directory / "input.json"), sha(self.directory / "input.json")),
            ),
            self.directory / "journal.json",
            self,
            stages=STAGES,
        )

    def result(self):
        ledger = read_json(self.pipe.ledger)
        return {
            "state": "retention_complete",
            "scientific_state": "held_unaccepted",
            "scientific_acceptance": False,
            "native_reward_accepted": False,
            "original_journal_unchanged": sha(self.pipe.directory / "journal.json")
            == self.source["original_files_sha256"]["journal.json"],
            "owned_cleanup_verified_empty": True,
            "new_primary_or_model_calls": 0,
            "cleanup_job_id": "/exedev/" + self.pipe.group["run_id"] + "-cleanup",
            "admission_control_unchanged": True,
            "admission_closed": bool(
                ledger.get("admission_closed") or ledger.get("model_admission_closed")
            ),
            "public_base": read_json(self.directory / "cleanup-proof.json")[
                "protected_public_base"
            ],
            "primary_publication": read_json(self.directory / "publication.json"),
            "cleanup_publication": read_json(self.directory / "cleanup/publication.json"),
        }


def run(output, *, publish=False, cleanup=False):
    plan, original = verify(output)
    results = []
    for group in original["tasks"]:
        directory = Path(plan["original_root"]) / "runs" / group["id"]
        if not (directory / "held.json").exists():
            results.append({"task_id": group["id"], "state": "not_held"})
            continue
        if read_json(directory / "held.json").get("reason") != evidence.ERROR:
            results.append(
                {
                    "task_id": group["id"],
                    "state": "unsupported_hold",
                    "original_held_unchanged": True,
                }
            )
            continue
        with lock(directory / "journal.json.lock"):
            actor = Retention(output, plan, group["id"], publish=publish, cleanup=cleanup)
            state = actor.step()
        if state == "complete":
            results.append({"task_id": group["id"], **actor.result()})
            continue
        return {
            "state": state,
            "task_id": group["id"],
            "results": results,
            "scientific_acceptance": False,
        }
    state = (
        "held_unsupported"
        if any(row["state"] == "unsupported_hold" for row in results)
        else "retention_complete"
        if any(row["state"] == "retention_complete" for row in results)
        else "nothing_to_retain"
    )
    return {
        "state": state,
        "results": results,
        "scientific_acceptance": False,
        "new_primary_or_model_calls": 0,
    }
