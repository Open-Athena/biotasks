"""Read-only checks of archived bytes and recorded results; no model/science runs."""

import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "experiments/3-authoring-migration"
BASELINE = STUDY / "baseline"
RUNS = BASELINE / "prompt-experiments"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(local_source=False):
    report = {"scope": "Saved-byte integrity, navigation, counts and comparison consistency only",
              "errors": [], "hash_claims": [], "runs": []}
    errors = report["errors"]

    def check(condition, message):
        if not condition:
            errors.append(message)

    def hash_check(path, expected, claim):
        actual = digest(path) if path.is_file() else None
        check(actual == expected, f"Hash mismatch: {claim}: {path}")
        report["hash_claims"].append({"claim": claim,
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "expected": expected, "actual": actual})

    migration = read(STUDY / "migration.json")
    for item in migration["tracked_files"]:
        path = ROOT / item["destination"]
        hash_check(path, item["sha256"], "migration")
        check(path.stat().st_size == item["bytes"], f"Size mismatch: {path}")
    changed = [x for x in migration["tracked_files"] if x["change"] != "unchanged-context"]
    check(len(changed) == migration["tracked_changed_paths"], "Changed-path count mismatch")
    expected_paths = {ROOT / x["destination"] for x in migration["tracked_files"]}
    actual_paths = {p for p in BASELINE.rglob("*") if p.is_file()
                    and "local-helpers" not in p.relative_to(BASELINE).parts
                    and "historical-prompts" not in p.relative_to(BASELINE).parts}
    check(expected_paths == actual_paths, "Preserved source file set mismatch")

    local = read(STUDY / "runs/2026-09-30-migration/local-files.json")
    for item in local["files"]:
        if "destination" in item:
            hash_check(ROOT / item["destination"], item["sha256"], "recovered local helper")
        if local_source:
            hash_check(Path(local["source_root"]) / item["path"], item["sha256"], "retained local file")
    if local_source:
        actual = {str(p.relative_to(local["source_root"])) for p in Path(local["source_root"]).rglob("*") if p.is_file()}
        check(actual == {x["path"] for x in local["files"]}, "Local source inventory changed")

    links = 0
    # Immutable worker inputs/outputs include source locators and historical paths.
    # Navigation is checked in research prose, not rewritten into those artifacts.
    for path in STUDY.rglob("*.md"):
        if any(x in path.parts for x in ("outputs", "inputs", "historical-prompts")):
            continue
        if path.name in ("template.md", "resolved-prompt.md"):
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            target = unquote(target.split("#", 1)[0])
            if not target or ":" in target:
                continue
            check((path.parent / target).exists(), f"Broken local link: {path}: {target}")
            links += 1
    report["local_navigation_paths_checked"] = links
    report["link_scope"] = "Relative Markdown target paths; external URL availability and fragment anchors are not checked."

    def visit_hashes(value, parent, label):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "artifact_sha256":
                    for target, expected in child.items():
                        hash_check(parent / target, expected, label + "/" + key)
                else:
                    visit_hashes(child, parent, label + "/" + key)
        elif isinstance(value, list):
            for child in value:
                visit_hashes(child, parent, label)

    for run_path in sorted(RUNS.glob("*/run.json")):
        run = read(run_path)
        parent = run_path.parent
        label = parent.name
        visit_hashes(run, parent, label)
        prompt = run["prompt"]
        if "snapshot" in prompt:
            hash_check(parent / prompt["snapshot"], prompt["sha256"], label + "/template")
        else:
            hash_check(BASELINE / "historical-prompts/72008dd682-find-units.md",
                       prompt["template_sha256"], label + "/historical-template")
        hash_check(parent / prompt["resolved_snapshot"], prompt["resolved_sha256"], label + "/resolved")
        execution = run["execution"]
        for key in ("launch_message", "source_access"):
            if key + "_sha256" in execution:
                hash_check(parent / execution[key], execution[key + "_sha256"], label + "/" + key)
        records = {}
        for kind in ("units", "datasets"):
            records[kind] = [json.loads(line) for line in (parent / "outputs" / (kind + ".jsonl")).read_text().splitlines() if line.strip()]
        counts = {key: len(value) for key, value in records.items()}
        recorded_counts = run.get("outputs", run.get("review", {})).get("counts")
        check(counts == recorded_counts, f"Recorded count mismatch: {label}")
        unit_ids = [x["unit_id"] for x in records["units"]]
        dataset_ids = [x["dataset_id"] for x in records["datasets"]]
        check(len(unit_ids) == len(set(unit_ids)), f"Duplicate unit IDs: {label}")
        check(len(dataset_ids) == len(set(dataset_ids)), f"Duplicate data IDs: {label}")
        for unit in records["units"]:
            check(set(unit["dataset_ids"]) <= set(dataset_ids), f"Unknown data IDs: {label}/{unit['unit_id']}")
            check(set(unit["related_unit_ids"]) <= set(unit_ids), f"Unknown related units: {label}/{unit['unit_id']}")
        report["runs"].append({"run_id": label, "status": run["status"], **counts,
                               "template_sha256": prompt.get("sha256", prompt.get("template_sha256"))})

    for path in RUNS.glob("*/original-*.json"):
        original = read(path)
        check(hashlib.sha256(original["content"].encode()).hexdigest() == original["sha256"],
              f"Original embedded bytes mismatch: {path}")
    runner = read(RUNS / "2026-09-30-cli-runner.json")
    hash_check(RUNS / runner["snapshot"], runner["sha256"], "post-run CLI wrapper snapshot")

    # Repeated-template groups and the four CLI cells are comparisons, not rankings.
    for repo in ("bedtools", "scanpy", "mmseqs2", "deseq2", "ucsc"):
        a = RUNS / f"2026-09-30-round2-{repo}-luna/template.md"
        b = RUNS / f"2026-09-30-round3-{repo}-luna/template.md"
        check(a.read_bytes() == b.read_bytes(), f"Identical-prompt repeat mismatch: {repo}")
    matrix = read(RUNS / "2026-09-30-uncapped-model-effort-comparison.json")
    matrix_records = []
    template_hashes, resolved_hashes = set(), set()
    for name in matrix["runs"]:
        parent = RUNS / name
        run = read(parent / "run.json")
        metrics = read(parent / "runner-metrics.json")
        template_hashes.add(digest(parent / "template.md"))
        resolved_hashes.add(digest(parent / "resolved-prompt.md"))
        check(run["source_revision"] == matrix["source_revision"], f"Matrix source revision: {name}")
        with gzip.open(parent / "runner-events.jsonl.gz", "rt") as stream:
            events = collections.Counter()
            usage = None
            for line in stream:
                event = json.loads(line)
                events[event["type"]] += 1
                if event["type"] == "turn.completed":
                    usage = event["usage"]
        setting = name.removeprefix("2026-09-30-uncapped-deseq2-")
        summary = matrix["results"][setting]
        counts = run["outputs"]["counts"]
        check(counts["units"] == summary.get("units", summary.get("units_at_checkpoint")), f"Matrix units: {setting}")
        check(counts["datasets"] == summary.get("datasets", summary.get("datasets_at_checkpoint")), f"Matrix datasets: {setting}")
        check(metrics["elapsed_seconds"] == summary["wall_seconds"], f"Matrix time: {setting}")
        check(usage == summary["reported_tokens"], f"Matrix token usage: {setting}")
        if metrics["exit_status"] == 0:
            check(events["turn.completed"] == 1 and events["turn.failed"] == 0, f"CLI completion: {setting}")
            check((parent / "worker-final.txt").is_file(), f"Missing final response: {setting}")
        else:
            check(events["turn.failed"] == 1 and events["turn.completed"] == 0, f"CLI failure: {setting}")
            check(not (parent / "worker-final.txt").exists(), f"Unexpected blocked final: {setting}")
        matrix_records.append({"setting": setting, **counts, "exit_status": metrics["exit_status"],
                               "seconds": metrics["elapsed_seconds"], "event_types": dict(events)})
    check(len(template_hashes) == len(resolved_hashes) == 1, "Matrix prompt differences")
    check(template_hashes == {matrix["prompt_sha256"]}, "Matrix template claim")
    report["uncapped_matrix"] = matrix_records

    catalog_dir = RUNS / "2026-09-30-catalog-ucsc-luna-high"
    check(digest(BASELINE / "prompts/find-units.md") == digest(catalog_dir / "template.md"), "Catalog trial/live source template mismatch")
    text = (catalog_dir / "outputs/inspection.md").read_text()
    section = text.split("## Utilities command catalog: entry-level status", 1)[1].split("\n## ", 1)[0]
    entries = re.findall(r"^\| `([^`]+)` \| (.*?) \|$", section, re.M)
    entries.extend((name, "pending") for name in re.findall(r"^`([^`]+)`$", section, re.M))
    names = [x[0] for x in entries]
    counts = collections.Counter("inspected" if x[1].startswith("inspected:") else "pending" if x[1].lower().startswith("pending") else "unknown" for x in entries)
    saved_catalog = read(catalog_dir / "catalog-review.json")
    check(len(names) == len(set(names)) == saved_catalog["unique_accounted_entries"], "Catalog entry identities/count")
    check(counts["inspected"] == saved_catalog["inspected_entries"], "Catalog inspected count")
    check(counts["pending"] == saved_catalog["pending_entries"] and not counts["unknown"], "Catalog pending count")
    report["catalog"] = {"entries": len(names), **counts,
                         "scope": "Recounted saved table; no fresh binary/source inspection"}
    report["tracked_files_checked"] = len(expected_paths)
    report["run_records_checked"] = len(report["runs"])
    report["hash_claims_checked"] = len(report["hash_claims"])
    report["result"] = "pass" if not errors else "fail"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-retained-local-source", action="store_true")
    args = parser.parse_args()
    result = verify(args.check_retained_local_source)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("hash_claims", "runs")}))
    raise SystemExit(bool(result["errors"]))
