"""Check original panel assets against one candidate runtime; never prepare jobs."""

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
from launch_autonomous import require_source_only_seed  # noqa: E402
from launch_reference import autonomous_asset_paths, source_archive  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def composed_archive(repo, worker_revision, original_revision, config, assets):
    """Use original input blobs in an isolated Git index, never the live checkout.

    Some notebooks exist only in original input commits. A public worker commit
    is not their source revision. Compose their exact original paths/modes over
    the worker tree, then exercise the real launcher's archive selection. New
    Git objects/index remain in a disposable local clone; no job or run commit.
    """
    with tempfile.TemporaryDirectory(prefix="biotasks19-source-composition-") as directory:
        view = Path(directory) / "source"
        subprocess.run(
            [
                "git",
                "-c",
                "gc.auto=0",
                "clone",
                "--quiet",
                "--shared",
                "--no-checkout",
                str(repo),
                str(view),
            ],
            check=True,
        )
        subprocess.run(["git", "read-tree", worker_revision], cwd=view, check=True)
        records = (
            subprocess.check_output(
                [
                    "git",
                    "ls-tree",
                    "-r",
                    "-z",
                    original_revision,
                    "--",
                    *[":(literal)" + p for p in sorted(assets)],
                ],
                cwd=view,
            )
            .decode()
            .split("\0")
        )
        copied = set()
        for record in filter(None, records):
            fields, name = record.split("\t", 1)
            mode, kind, oid = fields.split()
            if kind != "blob" or mode not in {"100644", "100755"} or name not in assets:
                raise ValueError("Original source asset is not an ordinary tracked file")
            subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo", mode, oid, name],
                cwd=view,
                check=True,
            )
            copied.add(name)
        if copied != assets:
            raise ValueError("Original input revision lacks a declared source asset")
        tree = subprocess.check_output(["git", "write-tree"], cwd=view, text=True).strip()
        raw = source_archive(view, tree, config)
    if view.exists():
        raise ValueError("Disposable source view was not cleaned")
    return raw, tree


def check(repo, candidate, inventory, freezes, original_launches):
    rows = []
    if len({row["source_id"] for row in inventory["cases"]}) != len(inventory["cases"]):
        raise ValueError("Panel inventory repeats a source")
    for case in inventory["cases"]:
        number = case["source_payload_campaign"]
        raw = (original_launches / f"{number:03}-payload/campaign-config.json").read_bytes()
        claim = read(original_launches / f"{number:03}-submission.json")
        original = read(freezes / f"freeze-{number:03}.json")
        if (
            hashlib.sha256(raw).hexdigest() != claim["inputs"]["files"]["campaign-config.json"]
            or original["input_revision"] != claim["factory_revision"]
        ):
            raise ValueError("Original source configuration identity changed")
        recorded = json.loads(raw)
        # Select provenance assets only; no old campaign/model/policy/run budget
        # becomes a new execution configuration by inspecting this inventory.
        config = {key: recorded[key] for key in ("entrypoint", "seed_file", "notebook_file")}
        if recorded.get("source_notices_file"):
            config["source_notices_file"] = recorded["source_notices_file"]
        if config["entrypoint"] != "run_autonomous.py":
            raise ValueError("Panel source was not an autonomous notebook input")
        assets = autonomous_asset_paths(config)
        if assets != set(original["source_assets"]):
            raise ValueError("Original source asset selection differs from its freeze")
        raw_archive, source_tree = composed_archive(
            repo, candidate["public_source_checkpoint"], original["input_revision"], config, assets
        )
        runtime, observed = {}, {}
        with tarfile.open(fileobj=io.BytesIO(raw_archive)) as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile() or member.name in runtime or member.name in observed:
                    raise ValueError("Unsafe or ambiguous source archive member")
                data = archive.extractfile(member).read()
                digest = hashlib.sha256(data).hexdigest()
                (observed if member.name in assets else runtime)[member.name] = digest
                if (
                    member.name
                    == EXPERIMENT.relative_to(repo).as_posix() + "/" + config["seed_file"]
                ):
                    require_source_only_seed(json.loads(data))
        if runtime != candidate["runtime_files"] or observed != original["source_assets"]:
            raise ValueError("Source assets changed or panel runtimes are inconsistent")
        notebook_key = EXPERIMENT.relative_to(repo).as_posix() + "/" + config["notebook_file"]
        if observed[notebook_key] != case["original_source_sha256"]:
            raise ValueError("Notebook identity does not match the panel source")
        rows.append(
            dict(
                source_id=case["source_id"],
                domain=case["domain"],
                original_source_campaign=number,
                original_configuration_sha256=hashlib.sha256(raw).hexdigest(),
                source_archive_sha256=hashlib.sha256(raw_archive).hexdigest(),
                original_input_revision=original["input_revision"],
                composed_git_tree=source_tree,
                disposable_source_view_cleaned=True,
                source_assets=observed,
                same_candidate_runtime=True,
                seed_has_no_generated_task_or_answers=True,
            )
        )
    return dict(
        scope="Source readiness only. No biological dependency/data availability, rights, native execution or scientific outcome is established.",
        public_source_checkpoint=candidate["public_source_checkpoint"],
        runtime_files=len(candidate["runtime_files"]),
        sources_checked=len(rows),
        cases=rows,
        prior_failures_preserved=True,
        campaign_payload_prepared=False,
        funding_reserved=False,
        new_model_requests=0,
        new_jobs_or_sandboxes=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--original-freezes", type=Path, required=True)
    parser.add_argument("--original-launches", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve the previous panel readiness record")
    result = check(
        EXPERIMENT.parents[1],
        read(args.candidate),
        read(args.inventory),
        args.original_freezes,
        args.original_launches,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "scope",
                    "runtime_files",
                    "sources_checked",
                    "campaign_payload_prepared",
                    "funding_reserved",
                )
            }
        )
    )
