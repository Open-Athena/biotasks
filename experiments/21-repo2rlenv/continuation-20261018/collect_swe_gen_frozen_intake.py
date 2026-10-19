"""Resolve a preselected PR cohort with the unchanged native SWE-gen resolver.

Only public GitHub reads and schema validation occur; no models, builds, task
execution, manual fixture selection or source/statement repairs.
"""

import hashlib
import json
from pathlib import Path

from repo2rlenv.github import _run_gh
from repo2rlenv.pipelines.pr_runtime import _path_is_test
from repo2rlenv.pipelines.recipes.swe_gen.source import fetch_source
from repo2rlenv.spec.recipe_options import PRRecipeOptions

BASE = Path(__file__).resolve().parent


def main():
    selection = BASE / "swe-gen-final-intake-selection.json"
    plan = json.loads(selection.read_text())
    output = BASE / "swe-gen-final-intake"
    output.mkdir(exist_ok=False)
    rows = []
    for unit in plan["units"]:
        repository = unit["repository"]
        prefix = "Bio/" if repository == "biopython/biopython" else "skbio/"
        for number in unit["pull_requests"]:
            directory = output / unit["label"] / str(number)
            directory.mkdir(parents=True)
            row = {"repository": repository, "pull_request": number, "status": "source_resolution_started", "model_calls": 0, "task_fixes": 0}
            rows.append(row)
            try:
                raw = _run_gh(["api", f"repos/{repository}/pulls/{number}/files?per_page=100", "--paginate", "--slurp"])
                (directory / "changed-files.json").write_text(raw)
                changed = [item for page in json.loads(raw) for item in page]
                sources = [item["filename"] for item in changed if item["filename"].startswith(prefix) and not _path_is_test(item["filename"])]
                tests = [item["filename"] for item in changed if _path_is_test(item["filename"])]
                original = json.loads((BASE.parent / unit["previous_profile"]).read_text())["options"]
                # Repository setup is frozen once in the selection, never changed
                # after seeing a PR outcome. No old per-task fixture additions.
                original.update(source_paths=sources, test_paths=tests, test_selectors=[], private_test_paths=[], install_command=unit["install_command"], exclude_candidate_ids=[], target=3, max_candidates=10)
                options = PRRecipeOptions.model_validate(original)
                url = f"https://github.com/{repository}/pull/{number}"
                source = fetch_source(url, options)
                assert source["source_files"] == sources
                if not source["test_files"]:
                    raise ValueError("No changed tests available for the native SWE-gen profile")
                serialized = (json.dumps(source, indent=2) + "\n").encode()
                (directory / "source.json").write_bytes(serialized)
                profile = {"stage": "native_source_resolved_execution_pending", "recipe": "swe_gen", "source": {"kind": "pr", "urls": [url]}, "options": options.model_dump(mode="json"), "source_sha256": hashlib.sha256(serialized).hexdigest(), "run_id": "swe-gen-" + unit["label"] + "-pr" + str(number), "selection_rule": "Frozen before any API outcome; native source filtering and native test-file classifier, no manual fixture additions or post-failure fixes."}
                (directory / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
                row.update(status="native_source_resolved_runtime_pending", native_id=source["id"], head=source["head"], source_sha256=profile["source_sha256"], source_files=source["source_files"], changed_test_files=source["test_files"])
            except Exception as exc:
                row.update(status="native_source_or_schema_rejected", error_type=type(exc).__name__)
                if isinstance(exc, ValueError):
                    row["reason"] = str(exc)
            (output / "resolution.json").write_text(json.dumps({"stage": "native_source_intake_only_not_generation", "selection_sha256": hashlib.sha256(selection.read_bytes()).hexdigest(), "rows": rows, "model_calls": 0, "workers": 0, "task_fixes": 0}, indent=2) + "\n")
    print(json.dumps({"considered": len(rows), "source_resolved": sum(r["status"] == "native_source_resolved_runtime_pending" for r in rows), "model_calls": 0, "workers": 0, "task_fixes": 0}))


if __name__ == "__main__":
    main()
