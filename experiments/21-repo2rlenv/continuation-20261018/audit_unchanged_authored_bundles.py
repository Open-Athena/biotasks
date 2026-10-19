"""Check original author/export provenance without executing repository or model code."""

import ast
import hashlib
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(native, archive):
    assert sha(archive) == "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
    recipes = native / "src/repo2rlenv/pipelines/recipes"
    wanted = {"repository/export.py", "swe_smith/issue.py", "swe_smith/issue_prompt.md", "swe_flow/author.py",
              *{"swe_flow/" + name for name in ("docstring_prompt.md", "docstring_demonstrations.json", "specification_prompt.md", "specification_demonstrations.json")}}
    verified = {}
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            relative = "/".join(member.name.split("/")[5:])
            # The source archive has one root followed by src/repo2rlenv/pipelines/recipes.
            if relative in wanted:
                original = source.extractfile(member).read()
                assert original == (recipes / relative).read_bytes()
                verified[relative] = hashlib.sha256(original).hexdigest()
    assert set(verified) == wanted
    manifest_path = ROOT / "hf-validation-followup-snapshot-manifest.json"
    assert sha(manifest_path) == "9f4b6c401be15e34643c5a9c834084c0a3344d787c0af8df179b10a74d259686"
    manifest = json.loads(manifest_path.read_text())
    export_tree = ast.parse((recipes / "repository/export.py").read_text())
    suffix_node = next(n for n in ast.walk(export_tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "instruction" for t in n.targets))
    rows = []
    for label, author, task, cohort, model_file, field, config in (
        ("esty-ci", "skbio-author-03", "swe-smith-e3fc0018c5332295d4ab", "skbio-smith-controls-02", "models/e3fc0018c5332295d4ab", "issue", "swe-smith-skbio-worker.json"),
        ("observed-features", "skbio-flow-author-01", "swe-flow-c80f6a9306c83c7db638", "skbio-flow-controls-01", "models/c80f6a9306c83c7db638/specification", "markdown", "swe-flow-skbio-worker.json"),
    ):
        accepted_path = ROOT / f"evidence/{label}-acceptance/acceptance.json"
        accepted = json.loads(accepted_path.read_text())
        original = next(f for f in manifest["files"] if f["path"] == f"evidence/{cohort}/native-evidence.tar.gz")
        prefix = next(m["path"].split("/" + task + "/")[0] + "/" + task + "/" for m in original["members"] if "/" + task + "/" in m["path"])
        assets = {m["path"][len(prefix):]: m["sha256"] for m in original["members"] if m["path"].startswith(prefix)}
        assert assets == accepted["asset_sha256"] and len(assets) == 2036
        folder = ROOT / "evidence" / author
        author_record = next(r for r in json.loads((folder / "issues.json").read_text())["records"] if r["candidate_id"] == task.removeprefix("swe-smith-").removeprefix("swe-flow-"))
        response_path = folder / (model_file + ".json")
        response = json.loads(response_path.read_text())
        instruction = json.loads(response["response"]["content"])[field]
        assert instruction == author_record["issue" if field == "issue" else "instruction"]
        options = json.loads((ROOT / config).read_text())["options"]
        scope = {"instruction": instruction, "directory_collection": False,
                 "options": SimpleNamespace(source_paths=options["source_paths"], use_system_site_packages=options.get("use_system_site_packages", False))}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[suffix_node], type_ignores=[])), "native_instruction_suffix", "exec"), scope)
        assert hashlib.sha256(scope["instruction"].encode()).hexdigest() == assets["instruction.md"]
        requests = []
        stages = ["issue"] if field == "issue" else ["docstring", "specification"]
        for stage in stages:
            request_path = folder / (model_file + ".request.json") if stage == "issue" else folder / f"models/c80f6a9306c83c7db638/{stage}.request.json"
            request = json.loads(request_path.read_text())
            payload = json.loads(request["user"])
            assert not any("feedback" in key or "review" in key for key in payload)
            if stage == "issue":
                assert "e3fc0018c5332295d4ab" not in json.loads((folder / "review-feedback.json").read_text())
                tree = ast.parse((recipes / "swe_smith/issue.py").read_text())
                expr = next(k.value for n in ast.walk(tree) if isinstance(n, ast.Call) for k in n.keywords if k.arg == "system")
                expected = eval(compile(ast.Expression(expr), "native_issue_prompt", "eval"), {"files": lambda _: recipes / "swe_smith", "__package__": "unused"})
            else:
                tree = ast.parse((recipes / "swe_flow/author.py").read_text())
                fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "author")
                loop = next(n for n in fn.body if isinstance(n, ast.For))
                nodes = [n for n in loop.body if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("prompt", "demonstrations") for t in n.targets)) or (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == "prompt")]
                prompt_scope = {"files": lambda _: recipes / "swe_flow", "__package__": "unused", "stage": stage, "json": json}
                exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "native_flow_prompt", "exec"), prompt_scope)
                expected = prompt_scope["prompt"]
            assert expected == request["system"]
            requests.append({"stage": stage, "source": str(request_path.relative_to(ROOT)), "sha256": sha(request_path), "system_prompt_matches_frozen_native": True, "whole_user_payload_is_json_without_review_feedback_keys": True})
        rows.append({"task": task, "acceptance_source": str(accepted_path.relative_to(ROOT)), "acceptance_sha256": sha(accepted_path),
                     "original_export_asset_count": len(assets), "accepted_asset_set_and_hashes_match_original": True,
                     "original_archive_sha256": original["sha256"], "response_source": str(response_path.relative_to(ROOT)),
                     "response_sha256": sha(response_path), "author_output_equals_saved_model_content": True,
                     "instruction_change_is_only_native_standard_suffix": True, "requests": requests,
                     "task_specific_downstream_asset_changes_found": 0, "profile": config, "profile_sha256": sha(ROOT / config),
                     "unattended_full_pipeline_established_by_this_audit": False})
    return {"stage": "post_run_original_authored_content_and_bundle_provenance_assessment", "rows": rows,
            "verified_native_source_assets": verified, "source_snapshot_manifest_sha256": sha(manifest_path),
            "original_export_assets_matched": sum(row["original_export_asset_count"] for row in rows),
            "new_model_calls": 0, "target_repository_code_executed": False, "task_assets_changed": 0,
            "limits": ["Asset matching uses the archived original member index and acceptance hashes; this is not a new byte download or runtime trial.",
                       "Verified automatic content and an unchanged accepted bundle do not prove unattended orchestration or generic repository discovery.",
                       "Prompt/suffix reconstruction evaluates only frozen pipeline formatting expressions; no target or generated program is executed."]}


if __name__ == "__main__":
    report = run(Path(sys.argv[1]), Path(sys.argv[2]))
    (BASE / "unchanged-authored-bundle-provenance-assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"tasks": len(report["rows"]), "matched_assets": report["original_export_assets_matched"], "model_calls": 0, "task_changes": 0}))
