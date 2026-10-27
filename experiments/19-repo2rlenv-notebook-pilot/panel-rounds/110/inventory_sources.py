"""Inventory original panel inputs without generating tasks or reserving runs."""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from tarfile import open as open_tar


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    started = time.monotonic()
    checkout = Path(__file__).resolve().parents[4]
    experiment = Path(__file__).resolve().parents[2]
    prefix = experiment.relative_to(checkout).as_posix() + "/"
    baseline = json.loads(args.baseline.read_text())
    runtime_raw = args.runtime.read_bytes()
    runtime = json.loads(runtime_raw)
    for name, expected in runtime["runtime_files"].items():
        assert digest((checkout / name).read_bytes()) == expected, name
    rows = []
    for case in baseline["cases"]:
        number = case["campaign"]
        payload = args.private_root / f"launch/{number:03}-payload"
        claim = json.loads((args.private_root / f"launch/{number:03}-submission.json").read_text())
        config_raw = (payload / "campaign-config.json").read_bytes()
        assert digest(config_raw) == claim["inputs"]["files"]["campaign-config.json"]
        config = json.loads(config_raw)
        asset_keys = ["notebook_file", "seed_file"]
        if config.get("source_notices_file") is not None:
            asset_keys.append("source_notices_file")
        archive = payload / "biotasks.tar"
        with archive.open("rb") as stream:
            assert (
                hashlib.file_digest(stream, "sha256").hexdigest()
                == claim["inputs"]["files"]["biotasks.tar"]
            )
        with open_tar(archive) as source:
            assets = {key: source.extractfile(prefix + config[key]).read() for key in asset_keys}
        seeds = json.loads(assets["seed_file"])
        assert len(seeds) == 1
        seed = seeds[0]
        assert set(seed) <= {
            "id",
            "source",
            "title",
            "url",
            "source_revision",
            "source_sha256",
            "license",
            "provenance",
        }
        assert digest(assets["notebook_file"]) == seed["source_sha256"]
        assert seed["url"] == case["original_source_url"]
        rows.append(
            {
                "source_id": case["source_id"],
                "domain": case["domain"],
                "original_source_url": seed["url"],
                "original_source_revision": seed["source_revision"],
                "original_source_sha256": seed["source_sha256"],
                "source_payload_campaign": number,
                "source_assets": {
                    config[key]: {"sha256": digest(raw), "bytes": len(raw)}
                    for key, raw in assets.items()
                },
                "seed_has_no_task_question": True,
                "separate_notice_asset": config.get("source_notices_file"),
                "publication_rights_established_by_this_inventory": False,
                "new_reassessment_state": "not_started_by_this_inventory",
                "new_funding_or_execution": False,
            }
        )
    assert len({row["source_id"] for row in rows}) == len(rows)
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": "Input readiness only; no new task, model call, reservation or launch. Keep prior outcomes and separate current trial receipts authoritative.",
        "baseline_sha256": digest(args.baseline.read_bytes()),
        "runtime_identity_sha256": digest(runtime_raw),
        "public_worker_revision": runtime["public_runtime_revision"],
        "runtime_files_checked": len(runtime["runtime_files"]),
        "sources_checked": len(rows),
        "inventory_seconds": round(time.monotonic() - started, 3),
        "cases": rows,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))


if __name__ == "__main__":
    main()
