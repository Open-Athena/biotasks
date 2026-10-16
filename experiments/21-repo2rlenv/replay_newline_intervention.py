"""Replay frozen PR diffs through the real GitHub reader and Harbor emitter.

A fixture gh executable supplies previously captured bytes, with no credentials
or network. This isolates the reader/emitter intervention from live discovery.
It does not execute target code or establish full Harbor validation.
"""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

from repo2rlenv.emitter.harbor import write_harbor_task
from repo2rlenv.github import GitHubError, PullRequestSummary, _run_gh, fetch_pr_diff
from repo2rlenv.pipelines.pr_diff import PRDiffPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import PRDiffOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["baseline", "intervention"], required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.runtime_root.resolve()
    records = []
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "gh"
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "if sys.argv[1:] == ['fixture-error']:\n"
            "    os.write(2, 'fixture error: café\\n'.encode()); sys.exit(1)\n"
            "if sys.argv[1:] == ['fixture-json']:\n"
            "    os.write(1, b'{\"ok\": true}\\r\\n'); sys.exit(0)\n"
            "assert sys.argv[1:3] == ['pr', 'diff']\n"
            f"path = Path({str(root)!r}) / ('bedtools-' + sys.argv[3] + '-raw.diff')\n"
            "os.write(1, path.read_bytes())\n"
        )
        executable.chmod(0o755)
        os.environ["PATH"] = directory + os.pathsep + os.environ["PATH"]
        assert json.loads(_run_gh(["fixture-json"])) == {"ok": True}
        try:
            _run_gh(["fixture-error"])
        except GitHubError as exc:
            assert "fixture error: café" in str(exc)
        else:
            raise AssertionError("Expected fixture process error")
        configs = json.loads((root / "pr-diff-01/generation.json").read_text())
        config = next(r["config"] for r in configs if r["repository"] == "arq5x/bedtools2")
        pipeline = PRDiffPipeline(GenerationInput.model_validate(config), PRDiffOptions(limit=10))
        for number in [1067, 1083]:
            row = json.loads((root / f"newline-fixtures/pr-{number}.json").read_text())
            old_task = root / f"pr-diff-01/arq5x__bedtools2/arq5x__bedtools2-{number}"
            original = tomllib.loads((old_task / "task.toml").read_text())["metadata"]["repo2env"]
            pr = PullRequestSummary(
                number=number,
                title=row["title"],
                body=row["body"],
                state=row["state"],
                merged_at=row["mergedAt"],
                base_ref=row["baseRefName"],
                base_sha=original["ref"],
                head_sha=row["headRefOid"],
                is_draft=row["isDraft"],
                url=row["url"],
                changed_files=[f["path"] for f in row["files"]],
            )
            raw = (root / f"bedtools-{number}-raw.diff").read_bytes()
            diff = fetch_pr_diff("arq5x", "bedtools2", number)
            task = pipeline._build_task(pr, diff)
            path = write_harbor_task(task, args.output / "tasks")
            emitted = (path / "solution/patch.diff").read_bytes()
            workspace = root / f"pr-diff-01-application/arq5x__bedtools2-{number}"
            applied = subprocess.run(
                ["git", "apply", "--check", str((path / "solution/patch.diff").resolve())],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            record = {
                "pr": number,
                "mode": args.mode,
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "emitted_sha256": hashlib.sha256(emitted).hexdigest(),
                "exact_diff_bytes_preserved": raw == emitted,
                "patch_apply_exit_code": applied.returncode,
                "diagnostic": applied.stderr,
                "instruction_matches_original": (path / "instruction.md").read_bytes()
                == (old_task / "instruction.md").read_bytes(),
            }
            records.append(record)
        (args.output / "report.json").write_text(
            json.dumps(
                {
                    "stage": "frozen_input_reader_emitter_replay",
                    "mode": args.mode,
                    "json_and_utf8_error_contracts_pass": True,
                    "network_calls": 0,
                    "model_calls": 0,
                    "container_runs": 0,
                    "records": records,
                },
                indent=2,
            )
            + "\n"
        )
        expected = args.mode == "intervention"
        assert all(r["exact_diff_bytes_preserved"] == expected for r in records)
        assert all((r["patch_apply_exit_code"] == 0) == expected for r in records)
        assert all(r["instruction_matches_original"] for r in records)
        print(args.mode, "expected outcomes confirmed for", len(records), "frozen candidates")


if __name__ == "__main__":
    main()
