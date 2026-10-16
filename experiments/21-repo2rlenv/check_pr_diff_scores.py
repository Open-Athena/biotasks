"""Bounded scorer diagnostics, not container or scientific validation."""

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

from repo2rlenv.pipelines import _pr_diff_verifier as verifier


def score(oracle, predicted):
    components = {
        "format_valid": verifier.format_valid(predicted),
        "size_sanity": verifier.size_sanity(oracle, predicted),
        "file_targeting": verifier.file_targeting(oracle, predicted),
        "region_overlap": verifier.region_overlap(oracle, predicted),
        "similarity": verifier.similarity(oracle, predicted),
        "llm_judge": None,
    }
    value = max(0.0, min(1.0, verifier.combine(components, verifier._DEFAULT_WEIGHTS)))
    if components["size_sanity"] < verifier._CATASTROPHIC_SIZE_THRESHOLD:
        value = min(value, verifier._CATASTROPHIC_SIZE_CAP)
    return {"reward": value, "components": components}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = []
    for path in sorted(args.tasks.glob("*/*/task.toml")):
        task = path.parent
        metadata = tomllib.loads(path.read_text())["metadata"]["repo2env"]
        patch = (task / "solution/patch.diff").read_text()
        row = {
            "task": task.name,
            "source": metadata["reference"],
            "base": metadata["ref"],
            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        }
        if len(patch) > 50000:
            row["status"] = "skipped_local_size_bound"
            rows.append(row)
            continue
        unrelated = "diff --git a/unrelated.txt b/unrelated.txt\n--- a/unrelated.txt\n+++ b/unrelated.txt\n@@ -1 +1 @@\n-old\n+new\n"
        # A reversed change is a negative direction probe, not an executable
        # submission. Patch application is checked independently in a later stage.
        reverse = (
            "\n".join(
                "-" + line[1:]
                if line.startswith("+") and not line.startswith("+++")
                else "+" + line[1:]
                if line.startswith("-") and not line.startswith("---")
                else line
                for line in patch.splitlines()
            )
            + "\n"
        )
        probes = {"oracle": patch, "empty": "", "unrelated": unrelated, "reversed_changes": reverse}
        row["scores"] = {name: score(patch, prediction) for name, prediction in probes.items()}
        row["status"] = "pure_scorer_diagnostics_completed"
        dockerfile = (task / "environment/Dockerfile").read_text()
        row["oracle_not_embedded_in_dockerfile"] = "oracle.patch" not in dockerfile
        rows.append(row)
    args.output.write_text(
        json.dumps(
            {
                "stage": "pure_scorer_diagnostics",
                "judge": "disabled; no network or model calls",
                "limitations": "No Docker build, patch application, valid-alternative test, solver run, or Marin conversion. Reversed patch is a string-level probe, not proof of an executable wrong solution.",
                "tasks": rows,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "tasks": len(rows),
                "completed": sum(r["status"] == "pure_scorer_diagnostics_completed" for r in rows),
            }
        )
    )


if __name__ == "__main__":
    main()
