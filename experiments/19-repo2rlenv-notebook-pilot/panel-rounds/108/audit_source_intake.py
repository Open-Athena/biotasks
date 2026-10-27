"""Audit original seed intake for a plan without freezing or launching campaigns.

This operator check reads the original submitted payloads. It copies no task
artifacts, changes no runtime or funding, and does not establish scientific or
redistribution validity. The normal freeze and launch gates still apply.
"""

import argparse
import hashlib
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
SOURCE_KEYS = {"campaign", "notebook_file", "seed_file", "source_notices_file"}
SEED_KEYS = {
    "id",
    "source",
    "title",
    "url",
    "source_revision",
    "source_sha256",
    "license",
    "provenance",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit_case(row, launch, policy):
    number = row["source_payload_campaign"]
    payload = launch / f"{number:03}-payload"
    claim_path = launch / f"{number:03}-submission.json"
    claim = json.loads(claim_path.read_text())
    config_path = payload / "campaign-config.json"
    assert digest(config_path) == claim["inputs"]["files"]["campaign-config.json"]
    config = json.loads(config_path.read_text())
    assert {k: v for k, v in config.items() if k not in SOURCE_KEYS} == {
        k: v for k, v in policy.items() if k not in SOURCE_KEYS
    }
    assets = set()
    for key in SOURCE_KEYS - {"campaign"}:
        if config.get(key) is None:
            continue
        relative = PurePosixPath(config[key])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) == config[key] and str(relative) != "."
        assets.add(PREFIX + str(relative))
    packet = payload / "biotasks.tar"
    assert digest(packet) == claim["inputs"]["files"]["biotasks.tar"]
    selected = {}
    with tarfile.open(packet) as archive:
        for member in archive:
            if member.name not in assets:
                continue
            assert member.isfile() and member.name not in selected
            selected[member.name] = archive.extractfile(member).read()
    assert set(selected) == assets
    seeds = json.loads(selected[PREFIX + config["seed_file"]])
    assert isinstance(seeds, list) and len(seeds) == 1
    seed = seeds[0]
    assert set(seed) <= SEED_KEYS and len(seed) == 7
    assert "id" in seed or "source" in seed
    assert seed["url"] == row["original_source_url"]
    if "id" in seed:
        assert seed["id"] == row["source_id"]
    notebook = selected[PREFIX + config["notebook_file"]]
    assert hashlib.sha256(notebook).hexdigest() == seed["source_sha256"]
    document = json.loads(notebook)
    assert document["nbformat"] == 4 and isinstance(document["cells"], list)
    provenance = seed["provenance"]["notebook"]
    assert provenance["url"] == seed["url"]
    assert provenance.get("revision", provenance.get("source_revision")) == seed["source_revision"]
    assert provenance.get("sha256", provenance.get("source_sha256")) == seed["source_sha256"]
    return {
        "source_id": row["source_id"],
        "prior_campaign": number,
        "claim_sha256": digest(claim_path),
        "submitted_archive_sha256": digest(packet),
        "original_source_url": seed["url"],
        "original_source_revision": seed["source_revision"],
        "source_sha256": seed["source_sha256"],
        "notebook_bytes": len(notebook),
        "notebook_cells": len(document["cells"]),
        "seed_fields": sorted(seed),
        "source_asset_hashes": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(selected.items())
        },
        "policy_matches_baseline": True,
        "generated_task_artifacts_selected": False,
        "source_bytes_modified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--policy-baseline", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    launch = args.private_root / "launch"
    policy_path = launch / f"{args.policy_baseline:03}-payload/campaign-config.json"
    policy = json.loads(policy_path.read_text())
    plan = json.loads(args.plan.read_text())
    assert len({row["source_id"] for row in plan["cases"]}) == len(plan["cases"])
    rows = [audit_case(row, launch, policy) for row in plan["cases"]]
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "helper_sha256": digest(Path(__file__)),
        "plan_sha256": digest(args.plan),
        "policy_baseline": args.policy_baseline,
        "policy_sha256": digest(policy_path),
        "source_count": len(rows),
        "all_original_intakes_verified": True,
        "scientific_validity_or_redistribution_permission_established": False,
        "campaigns_frozen_or_launched": 0,
        "model_calls": 0,
        "new_funding": False,
        "cases": rows,
    }
    args.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({k: v for k, v in proof.items() if k != "cases"}))


if __name__ == "__main__":
    main()
