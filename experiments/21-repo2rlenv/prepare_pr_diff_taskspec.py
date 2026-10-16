"""Prepare unresolved Marin TaskSpec JSON for a native PR-diff Harbor bundle.

This preserves native reward semantics; it does not establish schema validity,
buildability, isolation, reward parity, or scientific correctness. Validate with
the recorded Marin revision before execution. Other recipe layouts are refused.
"""

import argparse
import base64
import hashlib
import json
import stat
import tomllib
from pathlib import Path

MARIN_REVISION = "45a044387ccd95ab698b4a592056aadaff961540"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metadata = tomllib.loads((args.task / "task.toml").read_text())
    if metadata["metadata"]["repo2env"]["pipeline"] != "pr_diff":
        raise ValueError("Only the inspected native PR-diff structure is supported")
    resources = {}
    manifest = []
    for file in sorted(args.task.rglob("*")):
        if file.is_symlink():
            raise ValueError("Symlink conversion requires a separate contract")
        if file.is_dir():
            continue
        path = file.relative_to(args.task).as_posix()
        if path not in ("instruction.md", "task.toml") and path.split("/")[0] not in (
            "environment",
            "solution",
            "tests",
        ):
            raise ValueError(f"Unmapped native asset: {path}")
        data = file.read_bytes()
        mode = f"{stat.S_IMODE(file.stat().st_mode):04o}"
        manifest.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "mode": mode})
        resources[path] = {
            "path": path.split("/", 1)[-1],
            "source": {"kind": "inline_file", "content_base64": base64.b64encode(data).decode()},
            "mode": mode,
        }
    if "environment/docker-compose.yaml" in resources:
        raise ValueError("Compose runtime semantics are not implemented by this converter")
    for required in (
        "environment/Dockerfile",
        "solution/solve.sh",
        "tests/test.sh",
        "tests/oracle.patch",
    ):
        if required not in resources:
            raise ValueError(f"Missing expected native asset: {required}")
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    importer = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    environment = {
        "capabilities": ["shell", "filesystem"],
        "command_semantics": "linux_process",
        "working_directory": "/workspace",
        "docker_build": {
            "files": [v for k, v in resources.items() if k.startswith("environment/")]
        },
    }
    task = {
        "schema_version": "0.27",
        "id": f"repo2rlenv-pr-diff/{digest}",
        "source": {
            "dataset": "Open-Athena/biotasks-issue-21",
            "revision": f"sha256:{digest}",
            "row": metadata["task"]["name"],
            "importer_revision": f"sha256:{importer}",
        },
        "context": {
            "events": [
                {
                    "type": "message",
                    "role": "user",
                    "content": (args.task / "instruction.md").read_text(),
                }
            ]
        },
        "environment_requirements": environment,
        "answer_type": "workspace_state",
        "answer_format": {"kind": "plain_text"},
        "output_paths": ["/workspace"],
        "resources": {
            "worker": [],
            "oracle": [v for k, v in resources.items() if k.startswith("solution/")],
            "verifier": [v for k, v in resources.items() if k.startswith("tests/")],
        },
        "grader": {
            "kind": "script",
            "argv": ["bash", "/tests/test.sh"],
            "cwd": "/workspace",
            "environment": environment,
            "answer_path": None,
            "artifacts": [
                {
                    "source": "/workspace",
                    "target": "/workspace",
                    "kind": "directory",
                    "missing": "error",
                }
            ],
            "reward": {
                "kind": "file",
                "files": [{"path": "/logs/verifier/reward.txt", "format": "number"}],
            },
            "timeout": metadata["verifier"]["timeout_sec"],
        },
        "tags": ["biology", "repo2rlenv", "pr_diff", "unvalidated"],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "task.json").write_text(json.dumps(task, indent=2) + "\n")
    (args.output / "conversion.json").write_text(
        json.dumps(
            {
                "status": "prepared_unvalidated",
                "marin_revision": MARIN_REVISION,
                "native_manifest": manifest,
                "native_manifest_sha256": digest,
                "importer_sha256": importer,
                "native_metadata": metadata,
                "reward_contract": "unchanged native scalar diff similarity; not functional correctness",
                "pending": [
                    "pinned schema validation",
                    "fresh build",
                    "native/converted reward parity",
                    "grader isolation and workspace capture checks",
                ],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
