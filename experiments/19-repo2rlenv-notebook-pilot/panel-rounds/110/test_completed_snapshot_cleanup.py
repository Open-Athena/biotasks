"""A completed repair must not disappear from post-run provider cleanup."""

import copy

import pytest
from verify_completed_snapshot_cleanup import collect_cleanup, verify_absence


class Snapshot:
    def __init__(self, repair=True):
        folders = ["setup-raw", "replay", "materialization-raw", "grading"]
        if repair:
            folders.append("grading-comparison-repair")
        self.values = {
            "pipeline.json": {
                "status": "validated",
                "autonomous": True,
                "operator_interventions": 0,
                "stages": [
                    {"name": name, "status": "completed"}
                    for name in [
                        "preparation",
                        "setup",
                        "replay",
                        "specification",
                        "construction",
                        "grading",
                        "native",
                    ]
                ],
                "quality_repair": {
                    "kind": "public_question_diagnosis",
                    "allowance_consumed": True,
                    "target": "public_question",
                },
            },
            "native/execution.json": {
                "task_resources": {"cpus": 4, "memory_mb": 8192, "storage_mb": 10240}
            },
        }
        for folder in folders:
            self.values.update(
                {
                    folder + "/configuration.json": {"campaign": "example-" + folder},
                    folder + "/sandbox-claim.json": {
                        "owner": "example-" + folder,
                        "id": folder,
                        "state": "created",
                        "resources": {"cpu": 4, "memory": 8, "disk": 10},
                    },
                    folder + "/cleanup.json": {"passed": True, "remaining": [], "sandboxes": []},
                }
            )
        for agent in ("oracle", "nop", "terminus-2"):
            owner = "example-native-" + agent
            self.values[f"native/{agent}/remote-job.json"] = {
                "state": "completed",
                "returncode": 0,
                "job_id": owner,
                "command": ["harbor", "run", "--ek", 'labels={"repo2rlenv.job":"' + owner + '"}'],
                "cleanup": {"passed": True, "remaining": [], "sandboxes": []},
            }
        self.rows = {name: {"sha256": "a" * 64} for name in self.values}

    def read_json(self, name):
        return copy.deepcopy(self.values[name])


CONFIG = {
    "campaign": "example",
    "task_policy": {"sandbox": {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False}},
}


class DaytonaNotFoundError(Exception):
    pass


class Provider:
    def __init__(self, present=None):
        self.present, self.ids, self.owners = present, [], []

    def get(self, identity, **kwargs):
        self.ids.append(identity)
        if identity == self.present:
            return object()
        raise DaytonaNotFoundError

    def list(self, query, **kwargs):
        self.owners.append(query["labels"]["repo2rlenv.job"])
        return []


@pytest.mark.parametrize("repair,expected", [(False, 7), (True, 8)])
def test_every_claim_and_owner_is_checked_even_with_empty_deletion_lists(repair, expected):
    snapshot = Snapshot(repair=repair)
    evidence, owners, claims, unrecorded = collect_cleanup(snapshot, CONFIG)
    provider = Provider()
    checked = verify_absence(provider, dict, evidence, owners, claims)
    assert len(owners) == expected and provider.owners == owners
    assert set(provider.ids) == checked == {row["id"] for row in claims}
    assert len(unrecorded) == 3
    if repair:
        assert "grading-comparison-repair" in checked
        assert "example-grading-comparison-repair" in owners


def test_remaining_repair_claim_blocks_cleanup_despite_empty_owner_filter():
    evidence, owners, claims, _ = collect_cleanup(Snapshot(), CONFIG)
    with pytest.raises(RuntimeError, match="claimed sandbox remains"):
        verify_absence(
            Provider(present="grading-comparison-repair"), dict, evidence, owners, claims
        )


@pytest.mark.parametrize(
    "defect",
    [
        "unapproved",
        "uncertain",
        "remaining",
        "missing",
        "duplicate_id",
        "extra_claim",
        "native_owner",
    ],
)
def test_unproved_or_incomplete_resources_are_refused(defect):
    snapshot = Snapshot()
    if defect == "unapproved":
        snapshot.values["pipeline.json"]["quality_repair"]["allowance_consumed"] = False
    elif defect in {"uncertain", "remaining"}:
        key = "creation_uncertain" if defect == "uncertain" else "remaining"
        snapshot.values["grading-comparison-repair/cleanup.json"][key] = True
    elif defect == "missing":
        del snapshot.values["grading-comparison-repair/cleanup.json"]
    elif defect == "duplicate_id":
        snapshot.values["grading-comparison-repair/sandbox-claim.json"]["id"] = "grading"
    elif defect == "extra_claim":
        snapshot.rows["unknown/sandbox-claim.json"] = {"sha256": "b" * 64}
    elif defect == "native_owner":
        snapshot.values["native/oracle/remote-job.json"]["command"][-1] = (
            'labels={"repo2rlenv.job":"other"}'
        )
    with pytest.raises((AssertionError, KeyError)):
        collect_cleanup(snapshot, CONFIG)


def test_historically_recorded_native_id_is_checked_without_inventing_the_other_ids():
    snapshot = Snapshot()
    snapshot.values["native/oracle/remote-job.json"]["cleanup"]["sandboxes"] = [
        {
            "id": "native-original-id",
            "deleted": True,
            "cpu": 4,
            "memory": 8,
            "disk": 10,
        }
    ]
    evidence, owners, claims, unrecorded = collect_cleanup(snapshot, CONFIG)
    provider = Provider()
    checked = verify_absence(provider, dict, evidence, owners, claims)
    assert "native-original-id" in checked
    assert len(checked) == len(claims) + 1 and len(unrecorded) == 2
    with pytest.raises(RuntimeError, match="recorded sandbox remains"):
        verify_absence(Provider(present="native-original-id"), dict, evidence, owners, claims)
