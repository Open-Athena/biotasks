"""Audited local upstream export, followed by a mechanically generated manifest.

No generation, network, Docker, model calls or task repairs happen here. The
caller supplies source-bound raw exports, their original bootstrap cache and
an operator-owned validation policy. A failed preparation never changes raw
inputs. Only a fully audited directory is atomically made available to validate.
"""

import importlib
import json
import os
import re
import shutil
import sys
import tomllib
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from biotasks.validation.files import inventory, json_sha, lock, read_json, require, sha, write_json

UPSTREAM = "27d04ee8203cd5b2f20c3997d13836e5f5b64238"
_guard = {"active": False}
_installed = False


@contextmanager
def local_only():
    global _installed
    if not _installed:

        def audit(event, args):
            if not _guard["active"]:
                return
            require(
                event
                not in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"},
                "Local exporter attempted an external operation: " + event,
            )
            if event == "open" and isinstance(args[0], str):
                name = str(Path(args[0]).resolve())
                require(
                    not any(
                        part in name
                        for part in (
                            ".codex/secrets/",
                            ".config/gh/",
                            ".config/coreweave/",
                            ".cache/huggingface/token",
                            ".git-credentials",
                            ".docker/config.json",
                        )
                    ),
                    "Local exporter attempted credential access",
                )

        sys.addaudithook(audit)
        _installed = True
    old = _guard["active"]
    old_bytecode = sys.dont_write_bytecode
    _guard["active"] = True
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        _guard["active"] = old
        sys.dont_write_bytecode = old_bytecode


def source_api(source, manifest, extra_modules):
    source = source.resolve()
    value = read_json(manifest)
    require(value["revision"] == UPSTREAM, "Unsupported upstream revision")
    total = 0
    for row in value["files"]:
        path = source / row["path"]
        require(
            path.resolve().is_relative_to(source) and path.is_file() and not path.is_symlink(),
            "Unsafe or missing upstream file",
        )
        total += path.stat().st_size
        require(total <= 32 * 1024**2 and sha(path) == row["sha256"], "Upstream source changed")
    sys.path[:0] = [str(source / "src"), str(extra_modules)]
    with local_only():
        tomli_w = importlib.import_module("tomli_w")
        integration = importlib.import_module("repo2rlenv.registry.integration")
    assert isinstance(integration.__file__, str) and isinstance(tomli_w.__file__, str)
    require(
        Path(integration.__file__).resolve() == source / "src/repo2rlenv/registry/integration.py",
        "Upstream import came from another installation",
    )
    require(
        Path(tomli_w.__file__).resolve().is_relative_to(extra_modules.resolve()),
        "TOML writer came from another installation",
    )
    return integration


def grading_contract(path):
    value = deepcopy(tomllib.loads(path.read_text()))
    metadata = value.get("metadata", {}).get("repo2env", {})
    metadata.pop("spec_version", None)
    metadata.pop("reproducibility", None)
    return value


def cache_bindings(native, raw, cache):
    tasks = native._list_task_dirs(raw)
    require(len(tasks) <= 100, "Export count exceeds local handoff bound")
    refs = native._bootstrap_image_refs(tasks)
    require(len(refs) == len(tasks), "Missing runtime environment")
    bindings = []
    for image in sorted({ref for ref, _ in refs}):
        require(
            image.startswith("local/r2e-bootstrap/"),
            "Only native local bootstrap images are supported",
        )
        owner, name, short = native._parse_local_tag(image)
        key = owner + "__" + name
        require(
            re.fullmatch(r"[a-z0-9_.-]+__[a-z0-9_.-]+", key)
            and re.fullmatch(r"[0-9a-f]{12,40}", short),
            "Invalid bootstrap image identity",
        )
        roots = [p for p in cache.iterdir() if p.name.casefold() == key]
        require(len(roots) == 1, "Missing or ambiguous bootstrap repository cache")
        root = roots[0]
        require(
            re.fullmatch(r"[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+", root.name)
            and root.is_dir()
            and not root.is_symlink(),
            "Unsafe bootstrap repository cache",
        )
        matches = sorted(p for p in root.iterdir() if p.name.startswith(short[:12]))
        require(len(matches) == 1, "Missing or ambiguous bootstrap cache identity")
        require(matches[0].is_dir() and not matches[0].is_symlink(), "Unsafe bootstrap slot")
        path = matches[0] / "bootstrap.json"
        require(path.is_file() and not path.is_symlink(), "Unsafe bootstrap record")
        saved = read_json(path)
        require(
            isinstance(saved.get("repo"), str)
            and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", saved["repo"])
            and saved["repo"].casefold() == owner + "/" + name
            and saved.get("image_tag") == image
            and isinstance(saved.get("ref"), str)
            and re.fullmatch(r"[0-9a-f]{40}", saved["ref"])
            and saved["ref"].startswith(short),
            "Bootstrap cache/image identity differs",
        )
        require(
            isinstance(saved.get("rebuild_cmds"), list) and bool(saved["rebuild_cmds"]),
            "No recorded bootstrap recipe",
        )
        bindings.append(
            {
                "image": image,
                "cache": path.relative_to(cache).as_posix(),
                "sha256": sha(path),
                "repo": saved["repo"],
                "ref": saved["ref"],
                "staging_root": key,
            }
        )
    return tasks, bindings


def verify_final(directory, binding):
    result = read_json(directory / "handoff.json")
    require(result["input_binding"] == binding, "Completed handoff inputs changed")
    require(
        inventory(directory / "prepared") == result["prepared_files"],
        "Prepared export bytes changed",
    )
    require(
        sha(directory / "validation-manifest.json") == result["validation_manifest_sha256"],
        "Validation policy changed",
    )
    return result


def _prepare(config, native, failpoint):
    raw = Path(config["raw_exports"]).resolve()
    cache = Path(config["bootstrap_cache"]).resolve()
    output = Path(config["output_directory"]).resolve()
    require(
        not output.is_relative_to(raw) and not output.is_relative_to(cache),
        "Output must be separate from original inputs",
    )
    raw_files, cache_files = inventory(raw), inventory(cache)
    source_manifest = Path(config["upstream_manifest"])
    require(
        sha(source_manifest) == config["upstream_manifest_sha256"],
        "Upstream source manifest changed",
    )
    require(
        json_sha(inventory(Path(config["upstream_extra_modules"])))
        == config["upstream_extra_modules_sha256"],
        "Upstream preparation dependency changed",
    )
    require(
        json_sha(raw_files) == config["raw_inventory_sha256"]
        and json_sha(cache_files) == config["cache_inventory_sha256"],
        "Original generation inputs changed",
    )
    template = config["validation_template"]
    require(
        set(template)
        <= {
            "schema_version",
            "id",
            "repo2rlenv_revision",
            "backend",
            "budget_ledger",
            "max_cpu_hours_per_task",
            "archive",
        },
        "Invalid validator policy template",
    )
    require(template.get("repo2rlenv_revision") == UPSTREAM, "Validator revision differs")
    publication = config.get("publication", {"eligible": False})
    tasks, caches = cache_bindings(native, raw, cache)
    binding = {
        "raw_files": raw_files,
        "cache_files": cache_files,
        "cache_bindings": caches,
        "configuration_sha256": json_sha(config),
        "upstream_revision": UPSTREAM,
        "handoff_code_sha256": sha(Path(__file__)),
    }
    output.mkdir(parents=True, exist_ok=True)
    intent = output / "input-binding.json"
    if intent.exists():
        require(read_json(intent) == binding, "Existing preparation belongs to different inputs")
    else:
        require(not any(output.iterdir()), "Unowned output directory is not empty")
        write_json(intent, binding)
    final = output / "handoff"
    if final.exists():
        return verify_final(final, binding)
    stage = output / "staging"
    # The persisted input intent owns this disposable staging directory. Local
    # preparation may safely restart from immutable raw input after interruption;
    # it never restarts generation or any external effect.
    if stage.exists():
        require(stage.is_dir() and not stage.is_symlink(), "Unsafe staging directory")
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copytree(raw, stage / "prepared")
    shutil.copytree(cache, stage / "workspace/bootstrap")
    require(
        inventory(raw) == raw_files and inventory(cache) == cache_files,
        "Input changed while copying",
    )
    require(
        inventory(stage / "prepared") == raw_files
        and inventory(stage / "workspace/bootstrap") == cache_files,
        "Staged inputs differ",
    )
    mappings = {row["cache"].split("/", 1)[0]: row["staging_root"] for row in caches}
    for original, canonical in sorted(mappings.items()):
        if original != canonical:
            target = stage / "workspace/bootstrap" / canonical
            require(not target.exists(), "Staged bootstrap cache collision")
            (stage / "workspace/bootstrap" / original).rename(target)
    staged_cache = inventory(stage / "workspace/bootstrap")
    failpoint("before_native_export")
    cwd = Path.cwd()
    try:
        os.chdir(stage)
        with local_only():
            native_result = native.prepare_dataset_for_push(
                stage / "prepared", hf_owner="open-athena", inline_dockerfile=True, pushed_by=None
            )
    finally:
        os.chdir(cwd)
    failpoint("after_native_export")
    require(
        inventory(stage / "workspace/bootstrap") == staged_cache,
        "Native exporter changed staged bootstrap evidence",
    )
    require(native_result.tasks_rewritten == len(tasks), "Not all raw exports were prepared")
    require(not native_result.image_pushed, "Local preparation pushed an image")
    prepared = inventory(stage / "prepared")
    before, after = {r["path"]: r for r in raw_files}, {r["path"]: r for r in prepared}
    require(set(before) == set(after), "Exporter added or removed task files")
    changed = sorted(name for name in before if before[name] != after[name])
    allowed = {
        str(task.relative_to(raw) / name)
        for task in tasks
        for name in ("environment/Dockerfile", "task.toml")
    }
    require(set(changed) <= allowed, "Exporter changed grading assets")
    for task in tasks:
        target = stage / "prepared" / task.relative_to(raw)
        require(
            grading_contract(task / "task.toml") == grading_contract(target / "task.toml"),
            "Exporter changed grading settings",
        )
        require(
            tomllib.loads((target / "task.toml").read_text())["metadata"]["repo2env"][
                "reproducibility"
            ]["mode"]
            == "inline_dockerfile",
            "Task is not portable inline output",
        )
    require(
        inventory(raw) == raw_files and inventory(cache) == cache_files,
        "Original generation inputs changed during preparation",
    )
    manifest = deepcopy(template)
    manifest["exports"] = [
        {
            "path": str(Path("prepared") / task.relative_to(raw)),
            "initializer": "native-inline",
            "publication": publication,
        }
        for task in tasks
    ]
    write_json(stage / "validation-manifest.json", manifest)
    result = {
        "input_binding": binding,
        "state": "prepared" if tasks else "zero_exports",
        "task_count": len(tasks),
        "native_result": asdict(native_result),
        "changed_files": changed,
        "prepared_files": prepared,
        "cache_root_mapping": mappings,
        "staged_cache_files": staged_cache,
        "validation_manifest_sha256": sha(stage / "validation-manifest.json"),
        "upstream_source_modified": False,
        "model_calls": 0,
        "remote_jobs": 0,
    }
    write_json(stage / "handoff.json", result)
    # The original cache is retained by the generation evidence. Its staging copy
    # is unnecessary once the official inline output and identities are recorded.
    shutil.rmtree(stage / "workspace")
    for file in stage.rglob("*"):
        if file.is_file():
            with file.open("rb") as stream:
                os.fsync(stream.fileno())
    for folder in [
        *sorted(
            (p for p in stage.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True
        ),
        stage,
    ]:
        descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    failpoint("before_commit")
    stage.rename(final)
    descriptor = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    failpoint("after_commit")
    return verify_final(final, binding)


def prepare(config, native, failpoint=lambda stage: None):
    output = Path(config["output_directory"]).resolve()
    require(
        not output.is_relative_to(Path(config["raw_exports"]).resolve())
        and not output.is_relative_to(Path(config["bootstrap_cache"]).resolve()),
        "Output must be separate from original inputs",
    )
    with lock(output.with_name(output.name + ".lock")):
        return _prepare(config, native, failpoint)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    require(
        sha(Path(config["upstream_manifest"])) == config["upstream_manifest_sha256"],
        "Upstream manifest differs before import",
    )
    native = source_api(
        Path(config["upstream_source"]),
        Path(config["upstream_manifest"]),
        Path(config["upstream_extra_modules"]),
    )
    result = prepare(config, native)
    print(
        json.dumps(
            {
                "state": result["state"],
                "tasks": result["task_count"],
                "model_calls": 0,
                "remote_jobs": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
