"""Freeze four remaining commit inputs before applying unchanged native filters."""

import dataclasses
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

from repo2rlenv.git_local import CommitInfo
from repo2rlenv.pipelines.commit_runtime import CommitRuntimePipeline, split_patch_and_test_patch
from repo2rlenv.spec.options import CommitRuntimeOptions

BASE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(arguments):
    result = subprocess.run(["gh", "api", *arguments], capture_output=True, timeout=90, check=True)
    assert len(result.stdout) < 4 * 1024**2
    return result.stdout


def main():
    counter = json.loads((BASE / "remaining-candidate-reconciliation.json").read_text())["units"]["commit_runtime/native@scikit-bio/scikit-bio"]
    assert counter["charged_candidate_attempts"] == 6 and counter["remaining_allowance"] == 4
    old = json.loads((BASE / "skbio-commit-bug-intake/selection.json").read_text())["selected_shas"]
    old += [row["sha"] for row in json.loads((BASE / "commit-runtime-intake-next/skbio-selection.json").read_text())["records"]]
    old += ["71912bf097087f23e97ae8f11d234d0d5286f6ae"]
    assert len(set(old)) == 6
    folder = BASE / "skbio-commit-final-intake"
    folder.mkdir(exist_ok=False)
    rule = {"stage": "selection_rule_frozen_before_api_read_and_native_filters",
            "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "repository": "scikit-bio/scikit-bio", "route": "commit_runtime/native",
            "previous_candidate_charge": 6, "maximum_new_selected_inputs": 4, "candidate_cap": 10,
            "exclude_previously_selected_sha": sorted(set(old)),
            "rule": "Search repo:scikit-bio/scikit-bio BUG, committer-date descending, first20 results; take first four unseen SHAs. No replacement after native metadata/structural rejection. Charge each selected input once, including filter rejections. No target execution or task repair."}
    (folder / "selection-rule.json").write_text(json.dumps(rule, indent=2) + "\n")
    raw = fetch(["search/commits", "--method", "GET", "-f", "q=repo:scikit-bio/scikit-bio BUG",
                 "-f", "sort=committer-date", "-f", "order=desc", "-f", "per_page=20"])
    (folder / "search-response.json").write_bytes(raw)
    response = json.loads(raw)
    assert not response["incomplete_results"]
    chosen = [row["sha"] for row in response["items"] if row["sha"] not in old][:4]
    assert len(chosen) == len(set(chosen)) == 4
    selection = {"stage": "source_inputs_selected_before_native_filters", "repository": rule["repository"],
                 "route": rule["route"], "selected_shas": chosen, "selected_input_charge": 4,
                 "previous_route_charge": 6, "cumulative_conservative_charge": 10,
                 "remaining_candidate_allowance": 0, "candidate_cap": 10,
                 "search_response_sha256": digest(raw), "selection_rule_sha256": digest((folder / "selection-rule.json").read_bytes()),
                 "metadata_screen_pending": True, "model_calls": 0, "runtime_executed": False}
    (folder / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    options = CommitRuntimeOptions(limit=1, clone_depth=2)
    pipeline = object.__new__(CommitRuntimePipeline)
    pipeline.options = options
    rows = []
    for sha in chosen:
        metadata = fetch(["repos/scikit-bio/scikit-bio/commits/" + sha])
        (folder / (sha + "-head-commit.json")).write_bytes(metadata)
        commit = json.loads(metadata)
        assert commit["sha"] == sha
        parents = [row["sha"] for row in commit["parents"]]
        text = commit["commit"]["message"].split("\n", 1)
        author = commit["commit"]["author"]
        info = CommitInfo(sha=sha, parent_sha=parents[0] if parents else "", parents=parents,
                          author_name=author["name"], author_email=author["email"], authored_at=author["date"],
                          subject=text[0], body=text[1].strip() if len(text) > 1 else "")
        reason = pipeline._metadata_filter(info)
        row = {"sha": sha, "parent": info.parent_sha, "metadata_filter": reason,
               "structural_filter": "not_reached", "native_commit_info": dataclasses.asdict(info),
               "source_files": [item["filename"] for item in commit["files"]],
               "metadata_sha256": digest(metadata), "runtime_executed": False}
        if reason is None:
            diff = fetch(["repos/scikit-bio/scikit-bio/commits/" + sha, "-H", "Accept: application/vnd.github.diff"])
            assert diff.startswith(b"diff --git ")
            (folder / (sha + ".diff")).write_bytes(diff)
            source, tests = split_patch_and_test_patch(diff.decode())
            row.update(diff_sha256=digest(diff), source_patch_sha256=digest(source.encode()), test_patch_sha256=digest(tests.encode()),
                       structural_filter="empty_source_patch" if not source.strip() else "no_test_patch" if not tests.strip() else pipeline._structural_filter(source, tests))
        rows.append(row)
    report = {"stage": "unchanged_native_metadata_and_structural_filters_only", "options": options.model_dump(mode="json"),
              "records": rows, "eligible_for_native_runtime": [row["sha"] for row in rows if row["metadata_filter"] is None and row["structural_filter"] is None],
              "selected_inputs_considered": 4, "model_calls": 0, "runtime_executed": False, "task_specific_fixes": 0}
    raw_report = json.dumps(report, indent=2) + "\n"
    (folder / "structural-screen.json").write_text(raw_report)
    selection.update(metadata_screen_pending=False, eligible_for_native_runtime=report["eligible_for_native_runtime"],
                     structural_screen_sha256=digest(raw_report.encode()))
    (folder / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"selected": 4, "metadata_rejections": sum(row["metadata_filter"] is not None for row in rows),
                      "eligible_for_runtime": report["eligible_for_native_runtime"], "model_calls": 0, "target_execution": False}))


if __name__ == "__main__":
    main()
