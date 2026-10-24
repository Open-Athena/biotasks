"""Exercise the pinned, unchanged local exporter with synthetic inputs only."""

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parent
REVISION = "27d04ee8203cd5b2f20c3997d13836e5f5b64238"
REF = "0123456789abcdef0123456789abcdef01234567"
IMAGE = "local/r2e-bootstrap/example__synthetic:" + REF[:12]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    return {
        str(p.relative_to(root)): {
            "sha256": digest(p.read_bytes()),
            "bytes": p.stat().st_size,
            "mode": stat.S_IMODE(p.stat().st_mode),
        }
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def contract(task):
    data = deepcopy(tomllib.loads((task / "task.toml").read_text()))
    metadata = data.get("metadata", {}).get("repo2env", {})
    metadata.pop("spec_version", None)
    metadata.pop("reproducibility", None)
    return data


def fixture(root, cache_root):
    task = root / "raw" / "example__synthetic-1"
    files = {
        "environment/Dockerfile": f"FROM {IMAGE}\nWORKDIR /workspace\nRUN echo per-task-overlay\n",
        "task.toml": '[verifier]\ntimeout_sec = 300\n[agent]\ntimeout_sec = 1800\n[environment]\ncpus = 1\nmemory_mb = 6144\n[metadata.repo2env]\nspec_version = "0.1.0"\n[metadata.repo2env.pr_runtime]\nbase_commit = "synthetic-base"\n',
        "instruction.md": "Synthetic export-interface probe. Not a biological task.\n",
        "tests/test.sh": "#!/bin/sh\necho synthetic-grader-never-executed\n",
        "solution/solve.sh": "#!/bin/sh\necho synthetic-oracle-never-executed\n",
    }
    for name, text in files.items():
        target = task / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        target.chmod(0o755 if name.endswith(".sh") else 0o644)
    cache = root / cache_root / "example__synthetic" / REF[:12] / "bootstrap.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({
        "ref": REF,
        "language": "python",
        "dockerfile_reconstruction": "FROM python:3.12-slim\n",
        "rebuild_cmds": ["echo synthetic-recorded-command-never-executed"],
        "test_cmds": ["python -m pytest"],
    }, indent=2) + "\n")
    shutil.copytree(root / "raw", root / "prepared")
    return task, root / "prepared" / task.name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--extra-modules", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.source_manifest.read_text())
    assert manifest["revision"] == REVISION
    for row in manifest["files"]:
        assert digest((args.source / row["path"]).read_bytes()) == row["sha256"]
    sys.path[:0] = [str(args.source / "src"), str(args.extra_modules)]

    forbidden = []
    def audit(event, values):
        if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            forbidden.append(event)
            raise AssertionError("External operation forbidden: " + event)
        if event == "open" and isinstance(values[0], str):
            name = str(Path(values[0]).resolve())
            if any(part in name for part in (".codex/secrets/", ".config/gh/", ".config/coreweave/", ".cache/huggingface/token", ".git-credentials", ".docker/config.json")):
                forbidden.append("credential_store_open")
                raise AssertionError("Credential store forbidden")
    sys.addaudithook(audit)
    from repo2rlenv.registry.integration import prepare_dataset_for_push
    import repo2rlenv.registry.integration as native
    assert Path(native.__file__).resolve() == args.source / "src/repo2rlenv/registry/integration.py"

    cases = []
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="export-probe-", dir=ROOT) as temporary:
        base = Path(temporary)
        for label, cache_root, expected in (
            ("configured_custom_cache", "bootstrap", "missing_recipe"),
            ("native_lookup_layout", "workspace/bootstrap", "prepared"),
        ):
            root = base / label
            raw, prepared = fixture(root, cache_root)
            before, original_contract = inventory(root / "raw"), contract(raw)
            os.chdir(root)
            try:
                result = prepare_dataset_for_push(root / "prepared", hf_owner="open-athena", inline_dockerfile=True, pushed_by=None)
            except RuntimeError as error:
                assert expected == "missing_recipe" and "no cached Dockerfile" in str(error)
                assert inventory(root / "raw") == before == inventory(root / "prepared")
                cases.append({"case": label, "outcome": expected, "error": str(error), "source_unchanged": True})
            else:
                assert expected == "prepared" and result.tasks_rewritten == 1
                assert result.mode == "inline_dockerfile" and not result.image_pushed
                after = inventory(root / "prepared")
                changed = sorted(k for k in before if before[k] != after[k])
                assert changed == ["example__synthetic-1/environment/Dockerfile", "example__synthetic-1/task.toml"]
                assert contract(prepared) == original_contract
                assert inventory(root / "raw") == before
                cases.append({"case": label, "outcome": expected, "native_result": asdict(result), "changed": changed, "grading_contract_preserved": True, "raw_preserved": True, "files_before": before, "files_after": after})
                shutil.copyfile(prepared / "environment/Dockerfile", ROOT / "synthetic-inline.Dockerfile")
                shutil.copyfile(prepared / "task.toml", ROOT / "synthetic-inline-task.toml")
            finally:
                os.chdir(cwd)
        empty = base / "empty"
        empty.mkdir()
        result = prepare_dataset_for_push(empty, hf_owner="open-athena", inline_dockerfile=True)
        assert result.tasks_rewritten == 0 and result.mode == "local_only"
        cases.append({"case": "zero_exports", "outcome": "zero_tasks_not_successful_task", "native_result": asdict(result)})
    assert not forbidden
    report = {
        "upstream_revision": REVISION,
        "source_manifest_sha256": digest(args.source_manifest.read_bytes()),
        "input_kind": "synthetic interface fixtures, not biological execution",
        "full_unmodified_upstream_api": True,
        "cases": cases,
        "network_connections": 0, "subprocesses": 0, "credential_reads": 0,
        "model_calls": 0, "remote_jobs": 0, "fixture_directories_removed": True,
    }
    (ROOT / "local-export-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cases": len(cases), "models": 0, "remote_jobs": 0, "temporary_fixture_cleanup": True}))


if __name__ == "__main__":
    main()
