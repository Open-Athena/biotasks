"""Freeze current runtime with exact source assets from an earlier source-only payload.

Creates a private Git input ref and local payload, never dispatches a worker.
The public revision supplies runtime; only configured source assets are copied.
"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--prior", type=int, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--baseline-round", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Directory for a new public freeze")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert not (output / f"freeze-{args.number:03}.json").exists()
    assert not (output / "runtime-identity.json").exists()
    repo = Path(__file__).resolve().parents[4]
    experiment = repo / "experiments/19-repo2rlenv-notebook-pilot"
    sys.path.insert(0, str(experiment))
    from launch_reference import autonomous_asset_paths, frozen_payload

    def git(*command, data=None, env=None):
        return subprocess.check_output(["git", *command], cwd=repo, input=data, env=env)

    assert not git("status", "--porcelain").strip()
    public_revision = git("rev-parse", "HEAD").decode().strip()
    launch = args.private_root / "launch"
    prior = launch / f"{args.prior:03}-payload"
    destination = launch / f"{args.number:03}-payload"
    assert not destination.exists()
    config = json.loads((prior / "campaign-config.json").read_text())
    config["campaign"] = f"autonomous-panel-{args.number:03}"
    selected = autonomous_asset_paths(config)
    with tarfile.open(prior / "biotasks.tar") as archive:
        assets = {name: archive.extractfile(name).read() for name in sorted(selected)}
    # Keep the independent original seed bytes, not another task's specification.
    seed_name = "experiments/19-repo2rlenv-notebook-pilot/" + config["seed_file"]
    assert assets[seed_name] == (prior / "seeds.json").read_bytes()
    with tempfile.TemporaryDirectory(prefix="biotasks19-source-freeze-") as temporary:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temporary) / "index")}
        git("read-tree", public_revision, env=env)
        for name, raw in assets.items():
            blob = git("hash-object", "-w", "--stdin", data=raw).decode().strip()
            git("update-index", "--add", "--cacheinfo", "100644", blob, name, env=env)
        tree = git("write-tree", env=env).decode().strip()
        revision = (
            git(
                "commit-tree",
                tree,
                "-p",
                public_revision,
                "-m",
                f"Private source-only inputs for campaign {args.number:03}",
            )
            .decode()
            .strip()
        )
        git("update-ref", f"refs/biotasks19/private-inputs/{args.number:03}", revision, "")
    files = frozen_payload(
        repo, revision=revision, upstream_archive=prior / "upstream.tar.gz", config=config
    )
    source_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in assets.items()}
    with tarfile.open(fileobj=io.BytesIO(files["biotasks.tar"])) as archive:
        runtime = {
            member.name: hashlib.file_digest(archive.extractfile(member), "sha256").hexdigest()
            for member in archive
            if member.isfile() and member.name not in assets
        }
    baseline = json.loads((args.baseline_round / "runtime-identity.json").read_text())[
        "runtime_files"
    ]
    assert runtime.keys() == baseline.keys()
    changed = sorted(name for name in runtime if runtime[name] != baseline[name])
    assert changed == [
        "experiments/19-repo2rlenv-notebook-pilot/source_operations.py",
        "experiments/19-repo2rlenv-notebook-pilot/test_source_operations.py",
    ]
    destination.mkdir(mode=0o700)
    for name, raw in files.items():
        (destination / name).write_bytes(raw)
    manifest = json.loads(files["inputs.json"])
    seed = json.loads(files["seeds.json"])[0]
    freeze = {
        "campaign": args.number,
        "source_id": seed.get("id") or seed.get("title") or seed["url"],
        "input_revision": revision,
        "private_input_ref_not_pushed": True,
        "public_runtime_revision": public_revision,
        "input_manifest_sha256": hashlib.sha256(files["inputs.json"]).hexdigest(),
        "payload_files": manifest["files"],
        "source_assets": source_hashes,
        "runtime_file_count": len(runtime),
        "source_assets_identical_to": args.prior,
        "only_runtime_changes_from_baseline": changed,
        "reserved_usd": "5.00",
        "no_prior_generated_task_answer_or_diagnostic_hints": True,
        "two_reference_tests_unchanged": True,
    }
    (output / f"freeze-{args.number:03}.json").write_text(json.dumps(freeze, indent=2) + "\n")
    (output / "runtime-identity.json").write_text(
        json.dumps(
            {
                "public_runtime_revision": public_revision,
                "runtime_files": runtime,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "campaign": args.number,
                "runtime_files": len(runtime),
                "changed": changed,
                "input_revision": revision,
                "new_models_or_resources": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
