"""Check oracle patch application against bounded pinned source-file downloads.

Does not execute downloaded code or build an environment. Fetches only old file
paths named by exported patches, at their recorded base commit, from public raw
GitHub. Retains file hashes and diagnostics for replay.
"""

import argparse
import hashlib
import json
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    downloaded = 0
    for config in sorted(args.tasks.glob("*/*/task.toml")):
        task = config.parent
        metadata = tomllib.loads(config.read_text())["metadata"]["repo2env"]
        patch_path = task / "solution/patch.diff"
        patch = patch_path.read_text()
        record = {"task": task.name, "base": metadata["ref"], "repo": metadata["repo"], "files": []}
        workspace = args.output / task.name
        workspace.mkdir()
        try:
            paths = sorted(set(line[6:] for line in patch.splitlines() if line.startswith("--- a/")))
            if len(paths) > 5 or "GIT binary patch" in patch:
                raise ValueError("Outside bounded text patch profile")
            for name in paths:
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts or '"' in name or "\t" in name:
                    raise ValueError("Unsupported path encoding")
                url = f"https://raw.githubusercontent.com/{metadata['repo']}/{metadata['ref']}/{urllib.parse.quote(name)}"
                with urllib.request.urlopen(url, timeout=30) as response:
                    content = response.read(2_000_001)
                if len(content) > 2_000_000 or downloaded + len(content) > 50_000_000:
                    raise ValueError("Source download bound exceeded")
                downloaded += len(content)
                target = workspace / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                record["files"].append({"path": name, "url": url, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
            result = subprocess.run(["git", "apply", "--check", str(patch_path.resolve())], cwd=workspace, capture_output=True, text=True, timeout=15, check=False)
            record.update(status="patch_applies" if result.returncode == 0 else "patch_does_not_apply", exit_code=result.returncode, diagnostic=result.stderr[:8000])
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            record.update(status="check_incomplete", diagnostic=f"{type(exc).__name__}: {exc}")
        records.append(record)
        (args.output / "report.json").write_text(json.dumps({"stage": "patch_application_check", "limitations": "Text files only; no container build, target-code execution, full checkout, or scientific grading.", "downloaded_bytes": downloaded, "tasks": records}, indent=2) + "\n")
        print(task.name, record["status"], flush=True)


if __name__ == "__main__":
    main()
