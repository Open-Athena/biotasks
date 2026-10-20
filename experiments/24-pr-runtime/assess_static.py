"""Apply pinned native filters to sampled PRs, caching complete diff evidence."""

import argparse
import datetime
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from native_filters import SOURCE_SHA256, load, pr_summary

ROOT = Path(__file__).resolve().parent


def fetch_diff(repo, number):
    folder = ROOT / "inventory/pr-diffs" / repo.replace("/", "__")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{number}.diff"
    receipt = path.with_suffix(".json")
    if not receipt.exists():
        temporary = path.with_suffix(".tmp")
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with temporary.open("wb") as output:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/pulls/{number}",
                 "-H", "Accept: application/vnd.github.diff"],
                stdout=output, stderr=subprocess.PIPE, timeout=60,
            )
        if result.returncode:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Diff request failed for {repo}#{number}: exit {result.returncode}")
        if temporary.stat().st_size > 10 * 1024**2:
            temporary.unlink()
            raise RuntimeError(f"Diff exceeds the declared 10 MiB inspection bound: {repo}#{number}")
        temporary.replace(path)
        receipt.write_text(json.dumps({
            "repository": repo, "number": number, "captured_at": started,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }, indent=2) + "\n")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != json.loads(receipt.read_text())["sha256"]:
        raise ValueError("Cached diff checksum mismatch")
    return raw.decode(), str(path.relative_to(ROOT))


def assess(source):
    pipeline, native = load(source)
    results = []
    for path in sorted((ROOT / "inventory/pr-cohorts").glob("*.json")):
        cohort = json.loads(path.read_text())
        for pr in cohort["selected"]:
            summary = pr_summary(pr)
            reason = pipeline._pre_filter(summary)
            row = {
                "repository": cohort["repository"], "number": pr["number"],
                "url": pr["url"], "stratum": cohort["stratum"],
                "native_source_sha256": SOURCE_SHA256,
                "stage": "static_only", "disposition": reason or "pending_diff",
            }
            if reason is None:
                diff, evidence = fetch_diff(cohort["repository"], pr["number"])
                row["diff_evidence"] = evidence
                files = native["_files_in_patch"](diff)
                row["native_parsed_file_count"] = len(files)
                row["api_changed_files"] = pr["changedFiles"]
                if len(files) != pr["changedFiles"]:
                    row["disposition"] = "unresolved_diff_coverage"
                else:
                    patch, tests = native["split_patch_and_test_patch"](diff)
                    row["source_files"] = native["_files_in_patch"](patch)
                    row["test_files"] = native["_files_in_patch"](tests)
                    row["new_test_functions"] = native["_count_new_test_funcs"](tests)
                    row["disposition"] = (
                        "empty_source_patch" if not patch.strip()
                        else "no_test_patch" if not tests.strip()
                        else pipeline._structural_quality_filter(patch, tests)
                        or pipeline._lite_filter(summary, patch)
                        or "statically_eligible"
                    )
            results.append(row)
        print(json.dumps({
            "repository": cohort["repository"],
            "sampled": len(cohort["selected"]),
            "dispositions": dict(Counter(
                row["disposition"] for row in results if row["repository"] == cohort["repository"]
            )),
        }), flush=True)
        # Checkpoint only completed repository cohorts; reruns use exact cached diffs.
        (ROOT / "inventory/static-assessment.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in results)
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", required=True, type=Path)
    assess(parser.parse_args().native_source)
