"""Hash the existing launcher's committed runtime archive without preparing a run."""

import argparse
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
from launch_reference import autonomous_asset_paths, source_archive  # noqa: E402


def checkpoint(repo, revision, configuration, expected_assets, output):
    if output.exists():
        raise FileExistsError("Preserve the previous source checkpoint")
    assets = autonomous_asset_paths(configuration)
    if assets != set(expected_assets):
        raise ValueError("Source selection differs from its original manifest")
    raw = source_archive(repo, revision, configuration)
    runtime, observed, modes = {}, {}, {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile() or member.name in runtime or member.name in observed:
                raise ValueError("Source archive has links, special or duplicate members")
            digest = hashlib.file_digest(archive.extractfile(member), "sha256").hexdigest()
            (observed if member.name in assets else runtime)[member.name] = digest
            modes[member.name] = member.mode
    if observed != expected_assets:
        raise ValueError("Original source assets changed")
    baseline = json.loads(
        (EXPERIMENT / "panel-rounds/110/candidate-runtime-identity.json").read_text()
    )["runtime_files"]
    result = dict(
        status="source_checkpoint_only_not_funded_or_dispatched",
        public_source_checkpoint=revision,
        archive_sha256=hashlib.sha256(raw).hexdigest(),
        archive_bytes=len(raw),
        baseline_files=len(baseline),
        runtime_files=runtime,
        changed_or_added_files={
            name: dict(before=baseline.get(name), after=sha)
            for name, sha in runtime.items()
            if baseline.get(name) != sha
        },
        removed_files=sorted(baseline.keys() - runtime.keys()),
        original_assets_unchanged=observed,
        runtime_modes={name: modes[name] for name in runtime},
        campaign_payload_prepared=False,
        funding_reserved=False,
        new_model_requests=0,
        new_jobs_or_sandboxes=0,
    )
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision")
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--original-freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = checkpoint(
        EXPERIMENT.parents[1],
        args.revision,
        json.loads(args.configuration.read_text()),
        json.loads(args.original_freeze.read_text())["source_assets"],
        args.output,
    )
    print(
        json.dumps(
            {k: result[k] for k in ("status", "archive_bytes", "baseline_files")}
            | {
                "runtime_files": len(result["runtime_files"]),
                "source_deltas": len(result["changed_or_added_files"]),
                "removed_files": result["removed_files"],
            }
        )
    )
