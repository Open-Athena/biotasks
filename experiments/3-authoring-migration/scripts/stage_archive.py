"""Stage the reviewed local-file allowlist; preserve excluded originals in place."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "experiments/3-authoring-migration"
RECORD = STUDY / "runs/2026-09-30-archive-preparation"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    stage = Path(sys.argv[1]).resolve()
    stage.mkdir(parents=True, exist_ok=False)
    local = json.loads((STUDY / "runs/2026-09-30-migration/local-files.json").read_text())
    root = Path(local["source_root"])
    files, exclusions = [], []
    for item in local["files"]:
        source = root / item["path"]
        if source.stat().st_size != item["bytes"] or digest(source) != item["sha256"]:
            raise ValueError(f"Source changed: {item['path']}")
        if item["path"].startswith("source-review/2026-09-30/ucsc-"):
            exclusions.append(
                {
                    **item,
                    "disposition": "retained-at-source",
                    "reason": "UCSC cache excluded pending file-specific redistribution review. liftOver has custom terms; root license does not settle downloaded catalog/help or all directory overrides.",
                    "retention": "Retain original source-cache bytes; do not delete. No public upload or durable external archival is claimed.",
                }
            )
            continue
        target = stage / "source-cache" / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append(
            {
                "path": str(target.relative_to(stage)),
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "original_path": str(source),
            }
        )
    for source in sorted((RECORD / "licenses").iterdir()):
        if not source.is_file():
            continue
        target = stage / "notices" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append(
            {
                "path": str(target.relative_to(stage)),
                "bytes": source.stat().st_size,
                "sha256": digest(source),
                "original_path": str(source.relative_to(ROOT)),
            }
        )
    for source in (RECORD / "NOTICE.md",):
        target = stage / source.name
        shutil.copyfile(source, target)
        files.append(
            {
                "path": str(target.relative_to(stage)),
                "bytes": source.stat().st_size,
                "sha256": digest(source),
                "original_path": str(source.relative_to(ROOT)),
            }
        )
    result = {
        "source_root": str(stage),
        "files": files,
        "exclusions": exclusions,
        "provenance": {
            "original_local_inventory": "experiments/3-authoring-migration/runs/2026-09-30-migration/local-files.json",
            "original_local_inventory_sha256": digest(
                STUDY / "runs/2026-09-30-migration/local-files.json"
            ),
            "marin_revision": "37973a95c71d5e1d38bb15c238f1d40369255359",
            "source_cache_root": str(root),
            "retrieval_versions": "See source-cache/source-reviews/2026-09-29/sources.json and the per-run records. Missing historical pins remain unknown; notice capture is a later review, not proof of original retrieval.",
        },
        "eligibility": "Project-generated research records and unchanged Scanpy (BSD-3-Clause), STAR-DESeq2 workflow (MIT), MMseqs2 (MIT), DESeq2 (LGPL >=3), rnaseqGene (Artistic-2.0) source-cache files; notices accompany originals. Six UCSC files excluded. Logs contain public source retrievals with original URLs; no reasoning items or high-confidence credential patterns found in the inspected raw CLI event streams. Not a biological dataset release or relicensing.",
    }
    (RECORD / "allowlist.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "staged_files": len(files),
                "staged_bytes": sum(x["bytes"] for x in files),
                "excluded_files": len(exclusions),
                "stage": str(stage),
            }
        )
    )


if __name__ == "__main__":
    main()
