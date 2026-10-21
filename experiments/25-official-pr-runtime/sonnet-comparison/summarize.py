"""Summarize retained native evidence; never execute or repair an input."""

import ast
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EV = ROOT / "evidence"


def load(path):
    return json.loads(path.read_text())


def main():
    windows = load(EV / "native-windows.json")
    lifecycle = load(EV / "lifecycle.json")
    cleanup = load(EV / "supervisor-result.json")
    assert lifecycle["all_terminal"], "Final summary requires terminal jobs"
    assert all(not cleanup[name] for name in (
        "remaining_containers", "remaining_controllers", "remaining_images"
    )), "Owned cleanup is incomplete"
    baseline = load(ROOT.parent / "evidence/final-outcomes.json")
    exports = load(EV / "exported-tasks.json")
    repositories = {}
    window_records = []
    for window in windows:
        slug = window["window"]
        repo_slug = slug.rsplit("-", 1)[0]
        repository = repo_slug.replace("__", "/")
        log_path = EV / (slug + ".txt")
        log = log_path.read_text() if log_path.exists() else ""
        actions = re.findall(r"step=(\d+) action=(\w+) cost=\$([\d.]+)", log)
        if actions:
            assert repository not in repositories, "Unexpected second bootstrap"
            assert [int(row[0]) for row in actions] == list(range(len(actions)))
            folder = EV / "native/bootstrap" / repo_slug
            caches = list(folder.rglob("bootstrap.json"))
            assert len(caches) <= 1
            cached = load(caches[0]) if caches else None
            transcripts = list(folder.rglob("transcript.jsonl"))
            entries = sum(len(p.read_text().splitlines()) for p in transcripts)
            record = {
                "repository": repository,
                "agent_iterations": len(actions),
                "actions": dict(Counter(row[1] for row in actions)),
                "transcript_entries": entries,
                "bootstrap_saved": bool(cached),
                "sum_logged_rounded_estimated_usd": sum(float(row[2]) for row in actions),
                "stop_reason": "saved_native_bootstrap" if cached else (
                    "native_turn_limit" if "hit max_iterations=20" in log else "see_native_log"
                ),
            }
            if cached:
                record.update({key: cached.get(key) for key in (
                    "iterations", "image_tag", "image_digest", "smoke_passed",
                    "verify_passed", "verify_detail", "test_cmds", "llm_cost_estimate_usd"
                )})
            repositories[repository] = record
        candidate_match = re.search(r"candidates\s+(\d+)", log)
        emitted_match = re.search(r"emitted\s+(\d+)", log)
        skipped_match = re.search(r"skipped\s+(\d+)\s+\((\{[^\n]+\})\)", log)
        validations = []
        starts = list(re.finditer(r"running pre-fix stage at ([0-9a-f]+)", log))
        for index, start in enumerate(starts):
            block = log[start.end():starts[index + 1].start() if index + 1 < len(starts) else len(log)]
            parsed = re.search(r"parsed pre=(\d+) post=(\d+) tests; f2p=(\d+) p2p=(\d+)", block)
            row = {"base_prefix": start[1], "post_stage_started": "running post-fix stage" in block}
            if parsed:
                row.update(dict(zip(("pre_tests", "post_tests", "fail_to_pass", "pass_to_pass"), map(int, parsed.groups()), strict=True)))
            validations.append(row)
        record = {
            **window,
            "repository": repository,
            "candidates": int(candidate_match[1]) if candidate_match else None,
            "emitted": int(emitted_match[1]) if emitted_match else None,
            "skip_reasons": ast.literal_eval(skipped_match[2]) if skipped_match else None,
            "validation_attempts": validations,
            "stage_failure": "github_listing_timeout" if (
                "TimeoutExpired" in log and "'pr', 'list'" in log
            ) else None,
        }
        window_records.append(record)
    comparisons = []
    for target in load(ROOT.parent / "comparison-inputs.json"):
        window = next(w for w in window_records if w["window"] == target["repository"].replace("/", "__") + "-" + str(target["number"]))
        validations = [v for v in window["validation_attempts"] if target["baseRefOid"].startswith(v["base_prefix"])]
        comparisons.append({
            "repository": target["repository"], "number": target["number"],
            "validation_attempted": bool(validations), "validation_records": validations,
            "exported": any(target["repository"].replace("/", "__") + "-" + str(target["number"]) + "/task.toml" in p for p in exports),
            "attribution": "Native stage logs matched to the pre-run recorded PR base commit; absence of a stage marker does not identify its filter reason.",
        })
    counts = {
        "agent_iterations": sum(r["agent_iterations"] for r in repositories.values()),
        "invalid_actions": sum(r["actions"].get("INVALID", 0) for r in repositories.values()),
        "saved_bootstraps": sum(r["bootstrap_saved"] for r in repositories.values()),
        "native_candidates": sum(w["candidates"] or 0 for w in window_records),
        "native_validation_attempts": sum(len(w["validation_attempts"]) for w in window_records),
        "comparison_prs_validated": sum(r["validation_attempted"] for r in comparisons),
        "exports": len(exports),
    }
    result = {
        "model": load(ROOT / "launch-plan.json")["model"],
        "upstream_source_modifications": [], "counts": counts,
        "repositories": list(repositories.values()), "windows": window_records,
        "comparison_inputs": comparisons, "exported_tasks": exports,
        "glm_baseline_counts": baseline["counts"],
        "lifecycle": lifecycle, "cleanup": cleanup,
        "billed_model_usd": None, "token_usage": None,
        "api_request_count_including_sdk_retries": None,
        "cost_note": "Native estimates are not billed costs. Request IDs, token usage and resolved OpenRouter routing were not retained. No extra model call or repair was used.",
        "grading": "No exported tasks; no base/reference grading input exists." if not exports else "See separately retained official base/reference controls; export alone does not establish validity.",
        "diagnostic_limit": "Upstream does not persist rejected-stage raw logs. Aggregate skip reasons and parsed counts do not establish the exact underlying test failure.",
    }
    (EV / "final-outcomes.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
