"""Run the pinned native text-only generator; no bootstrap, model, or worker.

Invoke with the locked Repo2RLEnv Python interpreter. GitHub reads use normal
gh commands; token extraction and provider fallback are explicitly disabled.
"""

import argparse
import dataclasses
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from repo2rlenv.pipelines.pr_diff import PRDiffPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import PRDiffOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = Path(__file__).with_name("source-manifest.json")
    manifest = json.loads(manifest_path.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    # A named absent variable prevents native token resolution from reading an
    # unrelated process credential. gh itself retains its normal auth path.
    absent_key = "BIOTASKS21_NO_TOKEN_EXTRACTION"
    if absent_key in os.environ:
        raise RuntimeError("Reserved absent credential variable unexpectedly set")
    results = []
    for repo, revision in manifest["source_revisions"].items():
        if repo == "marin-community/marin":
            continue
        destination = args.output / repo.replace("/", "__")
        spec = GenerationInput.model_validate(
            {
                "repo": {"url": repo, "ref": revision, "access": "public"},
                "pipeline": {"name": "pr_diff", "options": {"limit": 10}},
                "output": {
                    "destination": str(destination),
                    "org": "Open-Athena",
                    "dataset_name": "biotasks21-pr-diff",
                    "visibility": "private",
                },
                "auth": {
                    "use_gh_cli": False,
                    "use_hf_cli": False,
                    "github_token_env": absent_key,
                },
                "bootstrap": {"enabled": False},
                "llm": None,
            }
        )
        record = {"repository": repo, "started_at": datetime.now(UTC).isoformat()}
        events = []
        pipeline = PRDiffPipeline(spec, PRDiffOptions(limit=10))
        pipeline.set_progress_callback(lambda **event: events.append(event))
        try:
            result = dataclasses.asdict(pipeline.run(destination))
            result["out_dir"] = str(result["out_dir"])
            record["result"] = result
            record["status"] = "generation_completed"
        except Exception as exc:
            record["status"] = "generation_failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["events"] = events
        record["ended_at"] = datetime.now(UTC).isoformat()
        record["config"] = spec.model_dump(mode="json")
        results.append(record)
        (args.output / "generation.json").write_text(json.dumps(results, indent=2) + "\n")
        print(repo, record["status"], record.get("result", {}).get("emitted"), flush=True)
    files = {}
    for path in sorted(args.output.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(args.output))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (args.output / "sha256.json").write_text(json.dumps(files, indent=2) + "\n")


if __name__ == "__main__":
    main()
