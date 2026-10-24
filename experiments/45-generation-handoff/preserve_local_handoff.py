"""Append-only public metadata snapshot; no task bytes, model traces or secrets."""

import argparse
import shutil
from pathlib import Path

from biotasks.validation import preservation
from biotasks.validation.archives import pack
from biotasks.validation.files import sha, write_json

ROOT = Path(__file__).resolve().parent
DIRECTORY = ROOT / "inputs-private/local-handoff-evidence"
POLICY = {
    "eligible": True,
    "review": "Reviewed exact own-source/check/provenance metadata allowlist only. No raw or prepared task code, bootstrap/model traces, credentials, biological datasets, images, environments or withheld Matchms. Upstream sources are referenced by immutable revision and digest, not redistributed in this snapshot.",
}
NAMES = [
    "preserve_local_handoff.py",
    "handoff.py",
    "test_handoff.py",
    "check_handoff.sh",
    "acquire_historical_reference.py",
    "check_historical_handoff.py",
    "probe_local_export.py",
    "local-export-probe.json",
    "source-manifest.json",
    "historical-acquisition-plan.json",
    "historical-acquisition.json",
    "historical-handoff-config.json",
    "historical-handoff-proof.json",
    "local-handoff-status.json",
    "handoff-boundary.json",
    "cost-preflight.json",
    "openrouter-endpoints.json",
    "proposed-protocol.md",
    "proposed-native-config.json",
    "logbook.md",
]
ARCHIVE = {
    "kind": "hf-public",
    "bucket": "open-athena/biotasks",
    "prefix": "research/45-generation-handoff",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "publish"])
    args = parser.parse_args()
    if args.action == "prepare":
        stage = DIRECTORY / "tree"
        stage.mkdir(parents=True)
        selected = [
            *NAMES,
            *[p.relative_to(ROOT).as_posix() for p in (ROOT / "local-checks").rglob("*.txt")],
        ]
        for name in selected:
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
            assert sha(ROOT / name) == sha(dest)
        shutil.copyfile(ROOT.parents[1] / "LICENSE", stage / "LICENSE")
        bundle = DIRECTORY / "evidence.tar.gz"
        package = pack(stage, bundle)
        preservation.inspect(bundle.read_bytes(), bundle.name)
        metadata = {
            "issue": 45,
            "source_checkpoint": "092f9054",
            "kind": "Historical local handoff and recovery evidence only",
            "fresh_generation": False,
            "native_controls_run": False,
            "model_calls": 0,
            "remote_jobs": 0,
            "historical_tasks_prepared_and_planned": 12,
            "offline_checks_passed": 11,
            "validation_runtime_commit": "1f6e7fe22e5c536a516eeef1aba105a59bfe944f",
            "public_policy": POLICY,
            "members": package["files"],
            "retention": "Retain while cited; no automatic deletion",
        }
        manifest = preservation.prepare(DIRECTORY, {"evidence.tar.gz": bundle}, metadata)
        write_json(ROOT / "local-handoff-evidence-manifest.json", manifest)
        assert sha(ROOT / "local-handoff-evidence-manifest.json") == sha(
            DIRECTORY / "preserved/manifest.json"
        )
        print(
            {
                "members": len(package["files"]),
                "bundle_bytes": bundle.stat().st_size,
                "manifest_sha256": sha(ROOT / "local-handoff-evidence-manifest.json"),
            }
        )
    else:
        assert sha(ROOT / "local-handoff-evidence-manifest.json") == sha(
            DIRECTORY / "preserved/manifest.json"
        )
        receipt = preservation.publish(DIRECTORY, ARCHIVE, POLICY)
        preservation.verify_receipt(DIRECTORY)
        write_json(ROOT / "local-handoff-hf-receipt.json", receipt)
        print(
            {
                "anonymous_download_verified": receipt["anonymous_download_verified"],
                "prefix": receipt["prefix"],
                "objects": len(receipt["objects"]),
            }
        )


if __name__ == "__main__":
    main()
