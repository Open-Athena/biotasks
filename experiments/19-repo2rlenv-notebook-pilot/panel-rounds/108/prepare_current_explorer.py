"""Select byte-verified original evidence for a published current-example viewer.

Presentation only; descriptions never become worker inputs or scientific artifacts.
"""

import argparse
import gzip
import hashlib
import json
import re
import tarfile
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]
BASE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("presentation", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    case = f"{args.number:03}"
    public = EXP / f"autonomous-runs/{case}"
    prefix = f"autonomous-runs/{case}/explorer-evidence/"
    dest = EXP / prefix
    assert not dest.exists()
    archive = BASE / f"archives/{case}"
    original = archive / ("snapshot-restored/files" if args.snapshot else "files")
    release = BASE / f"release{case}"
    verified = read(release / "anonymous-download-verification.json")
    assert verified["verified"] and verified["anonymous"]
    publication = read(release / "publication.json")
    profile = read(EXP / "explorer/current.json")
    previous = re.search(r"autonomous-runs/(\d+)/", profile["seed"]).group(1)

    def replace(value):
        if isinstance(value, str):
            return value.replace(
                f"autonomous-runs/{previous}/", f"autonomous-runs/{case}/"
            ).replace(f"autonomous-panel-{previous}", f"autonomous-panel-{case}")
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    profile = replace(profile)
    profile.update(read(args.presentation))
    # Optional stages belong to the selected execution, not the prior example.
    profile["stages"] = [
        stage
        for stage in profile["stages"]
        if not stage[0].startswith(
            ("specification-revision-", "specification-rereview-", "preparation-runtime-repair")
        )
    ]
    pipeline = read(original / "pipeline.json")
    assert pipeline["status"] == "validated" and not pipeline["operator_interventions"]
    profile["release"] = {
        "repository": publication["repo_id"],
        "publication": f"autonomous-runs/{case}/publication.json",
    }
    profile["program_revisions"] = {
        "release": read(release / "configuration.json")["release_stager_revision"]
    }
    profile["trajectory_glob"] = (
        prefix
        + str(
            Path("native") / read(original / "native/result.json")["solver"]["result_path"]
        ).rsplit("/", 1)[0]
        + "/agent/trajectory.json"
    )
    profile["verifier_report"] = (
        profile["trajectory_glob"].rsplit("/agent/", 1)[0] + "/verifier/report.json"
    )
    if args.snapshot:
        verified_snapshot = read(release / "primary-snapshot-verification.json")
        manifest_raw = (archive / "snapshot-restored/snapshot-files.json").read_bytes()
        assert verified_snapshot["archive_role"] == "primary"
        assert verified_snapshot["member_manifest_sha256"] == sha(manifest_raw)
        assert verified_snapshot["original_per_file_seal_reconstructed"] is False
    else:
        manifest_raw = (archive / "sealed-manifest.json").read_bytes()
    rows = {row["path"]: row for row in json.loads(manifest_raw)["files"]}
    selected = {}
    public.mkdir(parents=True, exist_ok=True)
    dest.mkdir()

    def put(name, raw, lineage):
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == raw
        else:
            path.write_bytes(raw)
        selected[name] = {"sha256": sha(raw), "bytes": len(raw), **lineage}

    def copy(name):
        raw = (original / name).read_bytes()
        row = rows[name]
        assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]
        put(name, raw, {"original_archive_path": name, "byte_preserved": True})

    def display(name, text, inputs):
        put(name, text.encode(), {"derived_display_document": True, "source_fields": inputs})

    for target, source in [
        ("publication.json", release / "publication.json"),
        ("hub-download-verification.json", release / "anonymous-download-verification.json"),
    ]:
        (public / target).write_bytes(source.read_bytes())
    payload = BASE / f"launch/{case}-payload"
    config = read(payload / "campaign-config.json")
    frozen = read(args.freeze or EXP / f"panel-rounds/108/freeze-{case}.json")
    assert frozen["campaign"] == args.number
    profile["runtime_revision"] = frozen["public_runtime_revision"]
    with tarfile.open(payload / "biotasks.tar") as source:
        for target, key in [("source.ipynb", "notebook_file"), ("seed.json", "seed_file")]:
            name = "experiments/19-repo2rlenv-notebook-pilot/" + config[key]
            raw = source.extractfile(name).read()
            assert sha(raw) == frozen["source_assets"][name]
            if target.endswith("ipynb"):
                put(
                    target + ".gz",
                    gzip.compress(raw, mtime=0),
                    {"uncompressed_sha256": sha(raw), "lossless_gzip": True},
                )
            else:
                put(target, raw, {"frozen_original_source_asset": name, "byte_preserved": True})

    def output_group(directory, document):
        paths = sorted(
            p
            for p in rows
            if p.startswith(directory + "/") and Path(p).suffix in {".csv", ".tsv", ".json"}
        )
        assert paths
        text = [
            "# Output artifacts",
            "",
            "Original values; no computation was repeated for this viewer.",
            "",
            "| Output | Bytes | SHA256 |",
            "| --- | ---: | --- |",
        ]
        for path in paths:
            row = rows[path]
            exact = [
                p
                for p, r in rows.items()
                if p.startswith(f"native/tasks/autonomous-panel-{case}/tests/reference/")
                and (r["sha256"], r["bytes"]) == (row["sha256"], row["bytes"])
            ]
            label = Path(path).name
            if exact:
                url = f"https://huggingface.co/datasets/{publication['repo_id']}/resolve/{publication['commit_sha']}/tasks/autonomous-panel-{case}/tests/reference/{Path(exact[0]).name}"
                label = f"[{label}]({url})"
            text.append(f"| {label} | {row['bytes']} | `{row['sha256']}` |")
            copy(path)
        display(document, "\n".join(text) + "\n", paths)
        return [[prefix + document, "Original output inventory"]] + [
            [prefix + p, Path(p).name] for p in paths
        ]

    initial_outputs = output_group("reference/trial/outputs", "reference-output-downloads.md")
    final_outputs = output_group("materialization/reference", "output-artifacts.md")
    by_id = {s[0]: s for s in profile["stages"]}
    repair = "preparation/runtime-repair"
    if repair + "/prepare/system-prompt.md" in rows:
        profile["stages"].insert(
            profile["stages"].index(by_id["worker"]) + 1,
            [
                "preparation-runtime-repair",
                "Repair terminal exports during setup",
                "GLM-5.3 · native high requested",
                "Within the preceding setup session, an export failure triggered the existing preparation repair. The worker received the recorded failure and repaired generated export code while preserving the original scientific source and selected endpoints.",
                "run_preparation.py",
                [
                    [
                        "Prompt",
                        [[prefix + repair + "/prepare/system-prompt.md", "Actual repair prompt"]],
                    ],
                    [
                        "Input",
                        [
                            [
                                prefix + repair + "/prepare/input.json",
                                "Recorded failure and repair input",
                            ]
                        ],
                    ],
                    [
                        "Output",
                        [
                            [prefix + repair + "/exports.py", "Repaired terminal-result exports"],
                            [prefix + repair + "/plan.json", "Recorded endpoint inventory"],
                            [prefix + repair + "/source.diff", "Append-only source difference"],
                        ],
                    ],
                ],
            ],
        )
    for key, heading, group in [
        ("worker", "Output artifacts", initial_outputs),
        ("materialize", "Reference outputs", final_outputs),
    ]:
        by_id[key][5] = [g for g in by_id[key][5] if g[0] != heading] + [[heading, group]]
    # Rebuild the variable review packet from this run; no previous packet paths survive.
    review = by_id["initial-review"]
    review[3] = (
        "Review scientific comparisons, source coverage, answer isolation and executed controls using this run's immutable evidence packet."
    )
    review[5] = [g for g in review[5] if g[0] != "Evidence available to the review tools"]
    descriptor = read(original / "grading/review/input.json")["review_evidence"]
    packet_name = (
        f"grading/review-inspection/review-packets/v1-{descriptor['context_sha256']}/manifest.json"
    )
    packet = read(original / packet_name)
    evidence = [[prefix + packet_name, "Complete identity-bound evidence index"]]
    for field, row in packet["fields"].items():
        path = str(Path(packet_name).parent / row["path"])
        assert rows[path]["sha256"] == row["sha256"]
        evidence.append([prefix + path, field])
    review[5].insert(-1, ["Evidence available to the review tools", evidence])
    # Include every specification review/repair that actually occurred, in order.
    reviews = pipeline.get("specification_reviews", [])
    insert = profile["stages"].index(by_id["specification-review"]) + 1
    for index, entry in enumerate(reviews[1:], 1):
        for key, directory, title, outputs in [
            (
                f"specification-revision-{index}",
                Path(entry["specification_directory"]).name,
                "Revise specification",
                ["specification.json", "task-brief.md", "validation-handoff.md"],
            ),
            (
                f"specification-rereview-{index}",
                Path(entry["review_directory"]).name,
                "Review revised specification",
                ["specification-review.json"],
            ),
        ]:
            assert rows.get(directory + "/specify/system-prompt.md")
            profile["stages"].insert(
                insert,
                [
                    key,
                    title,
                    "GLM-5.3 · native high requested",
                    "Recorded quality repair within the existing allowance; original and revised artifacts are separate.",
                    "run_specification.py",
                    [
                        [
                            "Prompt",
                            [
                                [
                                    prefix + directory + "/specify/system-prompt.md",
                                    "Actual system prompt",
                                ]
                            ],
                        ],
                        [
                            "Input",
                            [
                                [
                                    prefix + directory + "/specify/input.json",
                                    "Actual worker input JSON",
                                ]
                            ],
                        ],
                        ["Output", [[prefix + directory + "/" + p, p] for p in outputs]],
                    ],
                ],
            )
            insert += 1
    trajectory_name = profile["trajectory_glob"].removeprefix(prefix)
    trajectory = read(original / trajectory_name)
    display(
        "native/solver-input.md",
        trajectory["steps"][0]["message"],
        [trajectory_name + "#/steps/0/message"],
    )
    display(
        "native/harness-summary.json",
        json.dumps(
            {
                "agent": "terminus-2",
                "model": "glm-5.3",
                "solver_seconds": 600,
                "requested_effort": "high",
                "served_effort_verified": False,
                "connection_details_excluded": True,
            },
            indent=2,
        )
        + "\n",
        ["native/execution.json", "pipeline.json"],
    )
    for name in ["manifest.json", "release-files.json"]:
        put(
            "release/" + name,
            (release / "anonymous-download" / name).read_bytes(),
            {"verified_publication_revision": publication["commit_sha"], "byte_preserved": True},
        )

    def collect(value):
        if isinstance(value, str) and value.startswith(prefix):
            name = value.removeprefix(prefix)
            if name not in selected:
                copy(name)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)

    for number, stage in enumerate(profile["stages"], 1):
        stage[1] = f"{number:02} · {stage[1].split(' · ', 1)[-1]}"
    collect(profile)
    copy(f"native/tasks/autonomous-panel-{case}/environment/SOURCE-LICENSES.json")
    for name in selected:
        raw = (dest / name).read_bytes()
        assert b"/muchanem/" not in raw and b"glm53-relay" not in raw, name
    (public / "selected-evidence.json").write_text(
        json.dumps(
            {
                "campaign": args.number,
                "original_archive_manifest_sha256": sha(manifest_raw),
                "original_archive_format": "quiescent-tar-v1"
                if args.snapshot
                else "per-file-export-v1",
                "files": selected,
                "scientific_artifacts_modified": False,
                "publication_revision": publication["commit_sha"],
            },
            indent=2,
        )
        + "\n"
    )
    (EXP / "explorer/current.json").write_text(json.dumps(profile, indent=2) + "\n")
    print(
        json.dumps(
            {
                "current_example": args.number,
                "stages": len(profile["stages"]),
                "selected_files": len(selected),
                "solver_steps": len(trajectory["steps"]),
            }
        )
    )


if __name__ == "__main__":
    main()
