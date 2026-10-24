"""Freeze native-inline exports and execution policy before any remote effect."""

import math
import re
import shutil
import tempfile
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any

from biotasks.validation.archives import pack
from biotasks.validation.files import (
    ValidationError,
    content_sha,
    inventory,
    json_sha,
    lock,
    read_json,
    require,
    sha,
    write_json,
)
from biotasks.validation.recipes import native_prefix, tagged_recipe

UPSTREAM = "27d04ee8203cd5b2f20c3997d13836e5f5b64238"
TOOLS = {
    "controller_image": "python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1",
    "docker_url": "https://download.docker.com/linux/static/stable/x86_64/docker-23.0.6.tgz",
    "docker_sha256": "544262f4a3621222afb79960bfad4d486935dab80893478b5cc9cf8ebaf409ae",
    "compose_url": "https://github.com/docker/compose/releases/download/v2.30.3/docker-compose-linux-x86_64",
    "compose_sha256": "fbb4853d3f2148b0f2f0916f8971c9e500784e4e4949324934fc0b7dc2ed5016",
    "harbor_version": "0.6.6",
    "harbor_wheel_url": "https://files.pythonhosted.org/packages/0a/69/4ea696ff5cd29de03d784ed4348fefb843b19d5a2d67ba269a2c90cbedea/harbor-0.6.6-py3-none-any.whl",
    "harbor_wheel_sha256": "30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652",
    "harbor_wheel_filename": "harbor-0.6.6-py3-none-any.whl",
    "uv_version": "0.11.31",
    "tenacity_version": "9.2.1",
    "tenacity_wheel_url": "https://files.pythonhosted.org/packages/d6/26/1ff2b0721ac66a3ec5b1402b333110b352ab0a8724052ac279a7b82d40c4/tenacity-9.2.1-py3-none-any.whl",
    "tenacity_wheel_sha256": "9e56f17539296baab7beabb08b92f6ee3d7be92d8be72d763360677c2ad6580e",
    "tenacity_wheel_filename": "tenacity-9.2.1-py3-none-any.whl",
}


def code_files() -> dict[str, bytes]:
    """Package resources load identically from a checkout or installed wheel."""
    root = files("biotasks.validation")
    result: dict[str, bytes] = {}
    for entry in root.iterdir():
        if entry.is_file() and entry.name.endswith(".py"):
            result[entry.name] = entry.read_bytes()
    for entry in (root / "worker").iterdir():
        if entry.is_file() and entry.name.endswith((".py", ".sh")):
            result["worker/" + entry.name] = entry.read_bytes()
    return result


def code_identity() -> str:
    return json_sha({name: content_sha(raw) for name, raw in code_files().items()})


def number(value: Any, name: str, minimum: float, maximum: float) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"Invalid {name}")
    result = float(value)
    require(math.isfinite(result) and minimum <= result <= maximum, f"Invalid {name}")
    return result


def task_contract(path: Path) -> tuple[dict[str, Any], bytes]:
    rows = inventory(path)
    required = {
        "environment/Dockerfile",
        "environment/docker-compose.yaml",
        "task.toml",
        "instruction.md",
        "solution/solve.sh",
        "solution/patch.diff",
        "tests/f2p.json",
        "tests/p2p.json",
        "tests/test.sh",
        "tests/verifier.py",
    }
    require(
        required <= {row["path"] for row in rows}, "unsupported_export: incomplete pr_runtime task"
    )
    config = tomllib.loads((path / "task.toml").read_text())
    metadata = config.get("metadata", {}).get("repo2env", {})
    require(metadata.get("pipeline") == "pr_runtime", "unsupported_export: not pr_runtime")
    repo = metadata.get("repo", "")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "Missing source repository")
    base = metadata.get("pr_runtime", {}).get("base_commit")
    require(
        isinstance(base, str) and re.fullmatch(r"[0-9a-f]{40}", base), "Missing full base commit"
    )
    require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", path.name), "Invalid task directory name"
    )
    f2p = read_json(path / "tests/f2p.json")
    p2p = read_json(path / "tests/p2p.json")
    for ids in (f2p, p2p):
        require(
            isinstance(ids, list)
            and all(isinstance(v, str) for v in ids)
            and len(set(ids)) == len(ids),
            "Invalid tracked test IDs",
        )
    require(bool(f2p), "unsupported_export: empty F2P contract")
    seconds = number(
        config.get("verifier", {}).get("timeout_sec", 600), "native verifier timeout", 1, 7200
    )
    agent = number(
        config.get("agent", {}).get("timeout_sec", 1800), "native agent timeout", 1, 7200
    )
    prefix, base_ref = native_prefix((path / "environment/Dockerfile").read_bytes())
    tagged_recipe((path / "environment/Dockerfile").read_bytes(), "planning-check")
    # This exporter emits only an egress-guard overlay. Other Compose services
    # could escape the declared resource/ownership overlay, so are unsupported.
    compose = [
        line
        for line in (path / "environment/docker-compose.yaml").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        compose[:3] == ["services:", "  main:", "    extra_hosts:"]
        and all(re.fullmatch(r'      - "[A-Za-z0-9.-]+:0\.0\.0\.0"', line) for line in compose[3:]),
        "unsupported_export: expected native single-service egress guard",
    )
    environment = config.get("environment", {})
    require(
        environment.get("cpus", 1) == 1 and environment.get("memory_mb", 6144) == 6144,
        "unsupported_export: task resource profile differs",
    )
    identity = json_sha({"repo": repo, "task": path.name, "files": rows})
    return {
        "task": path.name,
        "repo": repo,
        "base_commit": base,
        "files": rows,
        "source_identity": identity,
        "expected_f2p": len(f2p),
        "expected_p2p": len(p2p),
        "verifier_seconds": seconds,
        "agent_seconds": agent,
        "public_base_ref": base_ref,
        "prefix_sha256": content_sha(prefix),
    }, prefix


def _prepare(manifest_path: Path, directory: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    require(isinstance(manifest, dict), "Manifest must be an object")
    require(
        set(manifest)
        <= {
            "schema_version",
            "id",
            "repo2rlenv_revision",
            "backend",
            "budget_ledger",
            "max_cpu_hours_per_task",
            "archive",
            "exports",
        },
        "Unknown manifest field",
    )
    require(
        isinstance(manifest.get("backend"), dict)
        and isinstance(manifest.get("exports"), list)
        and bool(manifest["exports"]),
        "Backend and nonempty exports are required",
    )
    require(manifest.get("schema_version") == 1, "Unsupported manifest version")
    name = manifest.get("id", "")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", name), "Invalid manifest id")
    require(manifest.get("repo2rlenv_revision") == UPSTREAM, "Unsupported exporter revision")
    backend = dict(manifest["backend"])
    require(
        set(backend)
        <= {
            "type",
            "python",
            "config",
            "worker_revision",
            "network",
            "excluded_worker_ids",
            "gcloud",
        },
        "Unknown backend field",
    )
    require(backend.get("type") == "iris", "Only existing-reserved Iris is supported")
    require(
        re.fullmatch(r"[0-9a-f]{10,40}", backend.get("worker_revision", "")),
        "Pin the worker revision",
    )
    for key in ("python", "config"):
        value = Path(backend[key]).expanduser()
        if not value.is_absolute():
            value = manifest_path.parent / value
        # Resolving the interpreter symlink loses its virtual environment.
        backend[key] = str(value.absolute() if key == "python" else value.resolve())
        require(value.is_file(), f"Missing backend {key}: {value}")
    backend.setdefault("network", "iris-egress")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", backend["network"]), "Invalid worker network")
    budget = Path(manifest["budget_ledger"]).expanduser()
    if not budget.is_absolute():
        budget = manifest_path.parent / budget
    require(budget.is_file(), "Create/adopt a CPU ledger before planning")
    limit = number(manifest.get("max_cpu_hours_per_task", 6), "CPU bound", 1, 32)
    archive = dict(manifest.get("archive", {"kind": "local"}))
    require(archive.get("kind") in ("local", "hf-public"), "Unsupported archive destination")
    if archive["kind"] == "hf-public":
        require(
            isinstance(archive.get("bucket"), str) and "/" in archive["bucket"], "Missing bucket"
        )
        require(
            isinstance(archive.get("prefix"), str)
            and re.fullmatch(r"[A-Za-z0-9_/.-]+", archive["prefix"]),
            "Invalid bucket prefix",
        )
        require(".." not in Path(archive["prefix"]).parts, "Invalid bucket prefix")
    require(not directory.exists(), "Never replace a planned run directory")
    directory.mkdir(mode=0o700, parents=True)
    tasks = []
    unsupported = []
    seen = set()
    for export in manifest["exports"]:
        require(
            isinstance(export, dict)
            and set(export) <= {"path", "initializer", "publication", "notices"},
            "Unknown export field",
        )
        source = Path(export["path"]).expanduser()
        if not source.is_absolute():
            source = manifest_path.parent / source
        require(source.is_dir() and not source.is_symlink(), f"Missing export directory: {source}")
        candidates = (
            [source]
            if (source / "task.toml").is_file()
            else sorted(p.parent for p in source.rglob("task.toml"))
        )
        require(len(candidates) <= 1000, "More than 1000 tasks in an export entry")
        for candidate in candidates:
            require(candidate.resolve() not in seen, "Duplicate input task")
            seen.add(candidate.resolve())
            try:
                require(
                    export.get("initializer", "native-inline") == "native-inline",
                    "unsupported_initializer: only native-inline is supported",
                )
                task, prefix = task_contract(candidate)
            except (ValidationError, tomllib.TOMLDecodeError, UnicodeError) as error:
                unsupported.append(
                    {"path": str(candidate), "state": "unsupported", "reason": str(error)}
                )
                continue
            # One immutable PR task per job: independent journals permit scheduling
            # without sharing task state, images or ownership across PRs.
            key = json_sha({"task": task, "policy": export.get("publication", {})})[:12]
            task_id = "task-" + key
            require(
                task_id not in {t["id"] for t in tasks},
                "Duplicate task content; list each task once",
            )
            target = directory / "tasks" / task_id
            tree = target / "tree" / "outputs" / task_id / task["task"]
            tree.parent.mkdir(parents=True)
            shutil.copytree(candidate, tree)
            require(inventory(tree) == task["files"], "Copied task differs")
            package = pack(target / "tree", target / "tasks.tar.gz")
            task["relative_directory"] = "outputs/" + task_id + "/" + task["task"]
            task["files"] = [
                {**row, "path": task["relative_directory"] + "/" + row["path"]}
                for row in task["files"]
            ]
            publication = dict(export.get("publication", {"eligible": False}))
            require(
                isinstance(publication.get("eligible"), bool),
                "Publication eligibility must be explicit",
            )
            notices = target / "notices"
            notices.mkdir()
            for index, notice in enumerate(export.get("notices", [])):
                path = Path(notice)
                if not path.is_absolute():
                    path = manifest_path.parent / path
                require(path.is_file() and not path.is_symlink(), "Missing source notice")
                shutil.copyfile(path, notices / f"{index:03d}-{path.name}")
            if publication["eligible"]:
                require(
                    bool(list(notices.iterdir())) and bool(publication.get("review")),
                    "Public artifacts need notices and a review record",
                )
            notice_bundle = pack(notices, target / "notices.tar.gz")
            wrapper = 2 * task["verifier_seconds"] + task["agent_seconds"] + 300
            seconds = math.floor(limit * 3600 / 2) - 300
            require(
                seconds - 300 >= 1200 + 600 + 2 * wrapper + 300,
                "CPU bound does not cover native controls and cleanup; increase max_cpu_hours_per_task",
            )
            tasks.append(
                {
                    "id": task_id,
                    "repo": task["repo"],
                    "task": task,
                    "prefix": prefix.decode(),
                    "package": {
                        **package,
                        "path": str((target / "tasks.tar.gz").relative_to(directory)),
                    },
                    "notices": {
                        **notice_bundle,
                        "path": str((target / "notices.tar.gz").relative_to(directory)),
                    },
                    "publication": publication,
                    "resources": {
                        "cpus": 2,
                        "memory_gib": 12,
                        "disk_gib": 24,
                        "controller_cpus": 0.5,
                        "task_cpus": 1,
                        "task_memory_gib": 6,
                        "timeout_seconds": seconds,
                        "work_deadline_seconds": seconds - 300,
                        "bootstrap_build_timeout_seconds": 1200,
                        "setup_timeout_seconds": 600,
                        "wrapper_seconds": wrapper,
                        "maximum_cpu_hours": limit,
                        "cleanup_cpu_hours": 1 / 6,
                    },
                }
            )
    normalized = {
        "schema_version": 1,
        "id": name,
        "manifest_sha256": sha(manifest_path),
        "repo2rlenv_revision": UPSTREAM,
        "code_identity": code_identity(),
        "backend": backend,
        "budget_ledger": str(budget.resolve()),
        "archive": archive,
        "tasks": tasks,
        "unsupported": unsupported,
        "model_calls_enabled": False,
        "new_capacity_allowed": False,
    }
    from biotasks.validation.bridge import call

    normalized["client_profile"] = call(
        backend, {"action": "fingerprint"}, directory / "client-profile.log"
    )
    normalized["backend_config_sha256"] = sha(Path(backend["config"]))
    identity = json_sha(normalized)
    normalized["plan_identity"] = identity
    for task in tasks:
        task["run_id"] = (
            "biotasks-val-"
            + name[:20]
            + "-"
            + json_sha({"plan": identity, "task": task["id"]})[:12]
        )
        compile_payload(directory, task, backend)
    (directory / "manifest.snapshot.json").write_bytes(manifest_path.read_bytes())
    write_json(directory / "plan.json", normalized)
    return normalized


def compile_payload(directory: Path, group: dict[str, Any], backend: dict[str, Any]) -> None:
    payload = directory / "tasks" / group["id"] / "payload"
    payload.mkdir()
    for name, raw in code_files().items():
        target = payload / "biotasks/validation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (payload / "biotasks/__init__.py").write_text('"""Bound standalone validation worker."""\n')
    task = group["task"]
    original = tomllib.loads(
        (
            directory / "tasks" / group["id"] / "tree" / task["relative_directory"] / "task.toml"
        ).read_text()
    )
    environment = original.get("environment", {})
    require(
        environment.get("cpus", 1) == 1 and environment.get("memory_mb", 6144) == 6144,
        "Unsupported declared task resource profile",
    )
    config = {
        "operation": "execute",
        "run_id": group["run_id"],
        "id": group["id"],
        "task": task,
        "resources": group["resources"],
        "tools": TOOLS,
        "network": backend["network"],
        "task_network": "none"
        if environment.get("allow_internet") is False
        else backend["network"],
        "package": group["package"],
        "bootstrap_prefix_sha256": task["prefix_sha256"],
    }
    write_json(payload / "family.json", config)
    shutil.copyfile(directory / group["package"]["path"], payload / "tasks.tar.gz")
    (payload / "bootstrap-prefix.Dockerfile").write_text(group["prefix"])
    (payload / "setup_controller.sh").write_bytes(
        (files("biotasks.validation.worker") / "setup_controller.sh").read_bytes()
    )
    (payload / "docker-launcher").write_text(
        "#!/usr/bin/env python3\nfrom biotasks.validation.worker.docker_bridge import main\nraise SystemExit(main())\n"
    )
    hashes = {p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()}
    write_json(payload / "payload.json", {"run_id": group["run_id"], "sha256": hashes})
    group["payload_directory"] = payload.relative_to(directory).as_posix()
    group["payload_sha256"] = {
        p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob("*") if p.is_file()
    }


def prepare(manifest_path: Path, directory: Path) -> dict[str, Any]:
    directory = directory.absolute()
    directory.parent.mkdir(parents=True, exist_ok=True)
    with lock(directory.parent / ("." + directory.name + ".planning.lock")):
        require(not directory.exists(), "Never replace an existing run directory")
        with tempfile.TemporaryDirectory(
            prefix=".validation-plan-", dir=directory.parent
        ) as temporary:
            staged = Path(temporary) / "run"
            result = _prepare(manifest_path, staged)
            staged.rename(directory)
            return result
