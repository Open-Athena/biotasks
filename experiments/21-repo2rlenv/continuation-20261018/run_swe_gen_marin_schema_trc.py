"""Read unchanged SWE-gen output and check a separate unresolved Marin mapping.

This integration assessment never edits the native task or executes its code.
It does not establish runtime parity or automatic-generation success.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from prepare_lcc_marin import prepare

REVISION = "45a044387ccd95ab698b4a592056aadaff961540"
TASK = "swe-gen-d52d9d8d8c952c886adb"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def assets(root):
    result = {}
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": digest(path), "mode": oct(path.stat().st_mode & 0o777)
            }
    return result


def check(output):
    from shellbox.machine import UnsupportedMachineSpec
    from taskcompendium.models import TaskSpec, require_resolved_environment

    raw = Path("mapping/task.json").read_bytes()
    spec = TaskSpec.model_validate_json(raw)
    assert spec.id.startswith("repo2rlenv-swe-gen/")
    assert not spec.resources.worker and not spec.resources.all
    assert spec.resources.oracle and spec.resources.verifier
    source = Path("native-task")
    decoded = json.loads(raw)
    for group, folder in (("oracle", "solution"), ("verifier", "tests")):
        for resource in decoded["resources"][group]:
            path = source / folder / resource["path"]
            assert base64.b64decode(resource["source"]["content_base64"], validate=True) == path.read_bytes()
            assert int(resource["mode"], 8) == path.stat().st_mode & 0o777
    for environment, folder in ((decoded["environment_requirements"], "environment"),
                                (decoded["grader"]["environment"], "tests")):
        for resource in environment["docker_build"]["files"]:
            path = source / folder / resource["path"]
            assert base64.b64decode(resource["source"]["content_base64"], validate=True) == path.read_bytes()
            assert int(resource["mode"], 8) == path.stat().st_mode & 0o777
    assert decoded["context"]["events"][0]["content"] == (source / "instruction.md").read_text()
    for environment in (spec.environment_requirements, spec.grader.environment):
        try:
            require_resolved_environment(environment)
        except UnsupportedMachineSpec:
            pass
        else:
            raise AssertionError("Unresolved build must not execute")
    record = {"stage": "exact_unchanged_SWE_gen_Marin_schema_only",
              "task_id": spec.id, "native_task_id": TASK, "marin_revision": REVISION,
              "task_spec_sha256": hashlib.sha256(raw).hexdigest(),
              "schema_validated": True, "inline_bytes_and_modes_verified": True,
              "learner_and_verifier_build_contexts_distinct": True,
              "unresolved_learner_and_verifier_execution_rejected": True,
              "worker_resources": 0, "oracle_resources": len(spec.resources.oracle),
              "verifier_resources": len(spec.resources.verifier),
              "native_task_changed": False, "target_code_executed": False,
              "model_calls": 0, "sandbox_allocations": 0, "runtime_parity": False,
              "Atlas_admitted": False,
              "limitations": ["No digest-resolved image or Marin execution tested.",
                             "Native network/user/resource restrictions require harness enforcement; schema acceptance does not prove them.",
                             "Conversion assessment is separate from automatic generation yield."]}
    (output / "schema-result.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0


def main():
    output = Path(os.environ["IRIS_OUTPUT_DIR"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert not os.environ.get("DAYTONA_API_KEY") and not os.environ.get("BIOTASKS21_GLM_KEY")
    if os.environ.get("BIOTASKS21_SCHEMA_CHILD") == "1":
        return check(output)
    started = time.monotonic()
    state = {"stage": "unchanged_SWE_gen_Marin_schema_setup", "status": "started",
             "model_calls": 0, "sandbox_allocations": 0, "target_code_executed": False}
    try:
        from huggingface_hub import HfApi

        manifest = json.loads(Path("manifest.json").read_text())
        remote = manifest["download"]
        archive_path = Path("native-evidence.tar.gz")
        HfApi(token=False).download_bucket_files(remote["bucket"], [(remote["path"], archive_path)],
                                               raise_on_missing_files=True, token=False)
        assert archive_path.stat().st_size == remote["bytes"] and digest(archive_path) == remote["sha256"]
        prefix = "native/authored/native-task/" + TASK + "/"
        task = Path("native-task")
        task.mkdir(exist_ok=False)
        total = 0
        with tarfile.open(archive_path, "r|gz") as archive:
            for member in archive:
                if not member.name.startswith(prefix) or member.isdir():
                    continue
                relative = Path(member.name.removeprefix(prefix))
                assert member.isfile() and not relative.is_absolute() and ".." not in relative.parts
                total += member.size
                assert total <= 256 * 1024**2 and member.size <= 48 * 1024**2
                destination = task / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    import shutil
                    shutil.copyfileobj(archive.extractfile(member), stream, 65536)
                destination.chmod(member.mode & 0o777)
        before = assets(task)
        identity = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()
        assert identity == manifest["native_asset_manifest_sha256"] and len(before) == 1980
        conversion = prepare(task, Path("mapping"))
        path = Path("mapping/task.json")
        mapped = json.loads(path.read_text())
        mapped["id"] = "repo2rlenv-swe-gen/" + identity
        mapped["source"]["importer_revision"] = "sha256:" + digest(Path(__file__))
        mapped["tags"] = ["biology-software", "repo2rlenv", "swe_gen", "conversion-unvalidated"]
        path.write_text(json.dumps(mapped, separators=(",", ":")) + "\n")
        assert assets(task) == before
        conversion.update(stage="separate_mapping_prepared_native_task_unchanged", task_id=mapped["id"],
                          task_json_sha256=digest(path), task_json_bytes=path.stat().st_size,
                          native_asset_manifest_sha256=identity, native_assets=1980,
                          native_asset_manifest=None)
        (output / "conversion.json").write_text(json.dumps(conversion, indent=2) + "\n")
        root = Path("schema-runtime")
        root.mkdir(exist_ok=False)
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        env["UV_PROJECT_ENVIRONMENT"] = str(root.resolve() / ".venv")
        with (output / "private-setup.log").open("w") as log:
            for command in (["git", "init", str(root)],
                            ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/marin-community/marin.git"],
                            ["git", "-C", str(root), "fetch", "--depth=1", "origin", REVISION],
                            ["git", "-C", str(root), "checkout", "--detach", "FETCH_HEAD"],
                            ["uv", "sync", "--frozen", "--no-dev", "--package", "marin-taskcompendium", "--python", "3.12.3", "--project", str(root)]):
                subprocess.run(command, env=env, stdout=log, stderr=log, check=True, timeout=600)
            assert subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() == REVISION
            env["BIOTASKS21_SCHEMA_CHILD"] = "1"
            result = subprocess.run([str(root.absolute() / ".venv/bin/python"), str(Path(__file__).absolute())],
                                    env=env, stdout=log, stderr=log, timeout=180)
        assert assets(task) == before
        state.update(status="schema_passed" if result.returncode == 0 else "schema_failed",
                     child_exit_code=result.returncode, original_native_assets_unchanged=True)
        return result.returncode
    except Exception as exc:
        state.update(status="setup_or_schema_failed", error_type=type(exc).__name__)
        return 1
    finally:
        state["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "wrapper-status.json").write_text(json.dumps(state, indent=2) + "\n")
        print(json.dumps(state), flush=True)


if __name__ == "__main__":
    sys.exit(main())
