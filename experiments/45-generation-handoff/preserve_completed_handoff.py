"""Preserve an explicit own-code/evidence allowlist after the native attempt."""

import argparse
import shutil
from pathlib import Path

from biotasks.validation import preservation
from biotasks.validation.archives import pack
from biotasks.validation.files import read_json, require, sha, write_json

ROOT = Path(__file__).resolve().parent
DIRECTORY = ROOT / "inputs-private/completed-handoff-evidence"
POLICY = {
    "eligible": True,
    "review": "Exact own-source, checks, source-reference metadata, terminal summaries and receipts only. Excludes raw/prepared tasks, bootstrap/model traces, fetched third-party sources, credentials, environments, biological datasets, images and withheld Matchms. Those eligible native originals have their own reviewed verified snapshots.",
}
ARCHIVE = {
    "kind": "hf-public",
    "bucket": "open-athena/biotasks",
    "prefix": "research/45-generation-handoff",
}
JSON = [
    "generation-terminal-summary.json",
    "completed-resume-proof.json",
    "generation-started.json",
    "generation-pre-rpc-cancellation.json",
    "generation-pre-rpc-observation.json",
    "generation-pre-rpc-budget.json",
    "generation-corrected-plan.json",
    "generation-corrected-pre-admission.json",
    "generation-corrected-price-quote.json",
    "actual-sdk-construction.json",
    "credential-preflight.json",
    "historical-handoff-proof.json",
    "local-handoff-hf-receipt.json",
    "local-handoff-cleanup.json",
    "source-manifest.json",
    "historical-handoff-config.json",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "publish"])
    parser.add_argument("--source-checkpoint", required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        tree = DIRECTORY / "tree"
        tree.mkdir(parents=True)
        selected = [
            *sorted(p.name for p in ROOT.glob("*.py")),
            *sorted(p.name for p in ROOT.glob("*.sh")),
            *sorted(p.name for p in ROOT.glob("*.md")),
            *JSON,
            *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "local-checks").rglob("*.txt")),
        ]
        require(len(selected) == len(set(selected)), "Duplicate selection")
        require(
            sum((ROOT / n).stat().st_size for n in selected) < 2 * 1024**2, "Metadata size bound"
        )
        for name in selected:
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            require(sha(target) == sha(ROOT / name), "Selected source changed")
        shutil.copyfile(ROOT.parents[1] / "LICENSE", tree / "LICENSE")
        bundle = DIRECTORY / "evidence.tar.gz"
        packed = pack(tree, bundle)
        preservation.inspect(bundle.read_bytes(), bundle.name)
        completed = read_json(ROOT / "generation-terminal-summary.json")
        require(completed["completed_connector"]["state"] == "complete", "Unfinished workflow")
        manifest = preservation.prepare(
            DIRECTORY,
            {"evidence.tar.gz": bundle},
            {
                "issue": 45,
                "source_checkpoint": args.source_checkpoint,
                "kind": "Fresh generation/unchanged failed rebuild, complete lifecycle evidence",
                "new_exports": 1,
                "new_unique_prs": 0,
                "independent_controls_started": 0,
                "provider_actual_usd": "0.287646",
                "upstream_model_calls": 11,
                "task_repairs": 0,
                "members": packed["files"],
                "public_policy": POLICY,
                "retention": "Retain while cited; no automatic deletion",
            },
        )
        write_json(ROOT / "completed-handoff-evidence-manifest.json", manifest)
        print({"members": len(packed["files"]), "bundle_bytes": bundle.stat().st_size})
    else:
        manifest = read_json(DIRECTORY / "preserved/manifest.json")
        require(
            manifest["metadata"]["source_checkpoint"] == args.source_checkpoint,
            "Checkpoint differs",
        )
        require(
            sha(ROOT / "completed-handoff-evidence-manifest.json")
            == sha(DIRECTORY / "preserved/manifest.json"),
            "Manifest changed",
        )
        receipt = preservation.publish(DIRECTORY, ARCHIVE, POLICY)
        preservation.verify_receipt(DIRECTORY)
        write_json(ROOT / "completed-handoff-hf-receipt.json", receipt)
        print(
            {
                "anonymous_download_verified": receipt["anonymous_download_verified"],
                "prefix": receipt["prefix"],
                "objects": len(receipt["objects"]),
            }
        )


if __name__ == "__main__":
    main()
