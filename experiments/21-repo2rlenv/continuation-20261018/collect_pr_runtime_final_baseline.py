"""Apply unchanged native PR-runtime intake filters to frozen unused inputs.

Public GitHub reads and static native filters only: no build, target execution,
authoring, task-specific configuration or output repair.
"""

import dataclasses
import hashlib
import json
from pathlib import Path

from repo2rlenv.github import PullRequestSummary, _run_gh, fetch_pr_diff
from repo2rlenv.pipelines.pr_runtime import PRRuntimePipeline, split_patch_and_test_patch
from repo2rlenv.spec.options import PRRuntimeOptions

BASE = Path(__file__).resolve().parent


def collect():
    selection = BASE / "pr-runtime-final-baseline-selection.json"
    plan = json.loads(selection.read_text())
    destination = BASE / "pr-runtime-final-baseline-intake"
    destination.mkdir(exist_ok=False)
    rows = []
    for unit in plan["units"]:
        owner, repo = unit["repository"].split("/")
        assert unit["prior_charged"] + len(unit["selected_prs"]) == 10
        options = PRRuntimeOptions.model_validate(unit["native_options"])
        # The three pure intake methods only read .options. Do not invent a
        # BootstrapResult or imply that a container/image has been prepared.
        filters = object.__new__(PRRuntimePipeline)
        filters.options = options
        for number in unit["selected_prs"]:
            folder = destination / unit["label"] / str(number)
            folder.mkdir(parents=True)
            row = {"repository": unit["repository"], "pr": number, "status": "started",
                   "model_calls": 0, "task_fixes": 0, "target_code_executed": False}
            rows.append(row)
            try:
                raw = _run_gh(["api", f"repos/{owner}/{repo}/pulls/{number}"])
                assert len(raw.encode()) <= 3 * 1024**2
                (folder / "github-pr.json").write_text(raw)
                api = json.loads(raw)
                pages = _run_gh(["api", f"repos/{owner}/{repo}/pulls/{number}/files?per_page=100", "--paginate", "--slurp"])
                assert len(pages.encode()) <= 8 * 1024**2
                (folder / "github-files.json").write_text(pages)
                changed = [item["filename"] for page in json.loads(pages) for item in page]
                pr = PullRequestSummary(number=api["number"], title=api["title"], body=api["body"] or "",
                    state=api["state"], merged_at=api["merged_at"], base_ref=api["base"]["ref"],
                    base_sha=api["base"]["sha"], head_sha=api["head"]["sha"],
                    is_draft=api["draft"], url=api["html_url"], changed_files=changed)
                assert pr.number == number
                (folder / "pr.json").write_text(json.dumps(dataclasses.asdict(pr), indent=2) + "\n")
                reason = filters._pre_filter(pr)
                if reason is None:
                    diff = fetch_pr_diff(owner, repo, number)
                    assert len(diff.encode()) <= 8 * 1024**2
                    (folder / "pr.diff").write_text(diff)
                    source, tests = split_patch_and_test_patch(diff)
                    reason = ("empty_source_patch" if not source.strip() else
                              "no_test_patch" if not tests.strip() else
                              filters._structural_quality_filter(source, tests) or filters._lite_filter(pr, source))
                    row.update(source_patch_bytes=len(source.encode()), test_patch_bytes=len(tests.encode()))
                row.update(status="native_filter_rejected" if reason else "native_runtime_pending",
                           native_filter=reason, base_sha=pr.base_sha, head_sha=pr.head_sha,
                           frozen_files={path.name: {"bytes": path.stat().st_size,
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                               for path in sorted(folder.iterdir())})
            except Exception as exc:
                row.update(status="API_or_static_intake_failed", error_type=type(exc).__name__)
            result = {"stage": "native_PR_runtime_static_intake_not_execution", "rows": rows,
                      "selection_sha256": hashlib.sha256(selection.read_bytes()).hexdigest(),
                      "selected_inputs_charged": 6, "model_calls": 0, "workers": 0,
                      "task_fixes": 0, "native_runtime_executions": 0, "new_admissions": 0}
            (destination / "intake.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"considered": len(rows), "runtime_pending": sum(row["status"] == "native_runtime_pending" for row in rows),
                      "model_calls": 0, "target_code_executed": False}))


if __name__ == "__main__":
    collect()
