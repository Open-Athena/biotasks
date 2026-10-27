"""Select unchanged recorded evidence for the latest qualified example viewer."""

import gzip
import hashlib
import json
import tarfile
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]
BASE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
ARCHIVE = BASE / "archives/215"
ORIGINAL = ARCHIVE / "files"
DEST = EXP / "autonomous-runs/215/explorer-evidence"
PREFIX = "autonomous-runs/215/explorer-evidence/"
PUBLIC = EXP / "autonomous-runs/215"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not DEST.exists()
    verified = json.loads((BASE / "release215/anonymous-download-verification.json").read_text())
    assert verified["verified"] and verified["anonymous"]
    publication = json.loads((BASE / "release215/publication.json").read_text())
    for name, source in [
        ("publication.json", BASE / "release215/publication.json"),
        (
            "hub-download-verification.json",
            BASE / "release215/anonymous-download-verification.json",
        ),
    ]:
        (PUBLIC / name).write_bytes(source.read_bytes())
    old_profile = json.loads((EXP / "explorer/current.json").read_text())

    def replace(value):
        if isinstance(value, str):
            return value.replace("autonomous-runs/198/", "autonomous-runs/215/").replace(
                "autonomous-panel-198", "autonomous-panel-215"
            )
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    profile = replace(old_profile)
    profile["stages"] = [
        stage for stage in profile["stages"] if stage[0] not in {"grader-repair", "repair-review"}
    ]
    profile.update(
        subtitle="PyMC · hierarchical rat-tumor inference",
        footer="Original MIT source notice and BDA3 attribution are retained. Recorded notebook, task and attempt; no live model calls.",
        notebook_title="PyMC · beta-binomial hierarchical modeling",
        notebook_description="The original tool-repository notebook computes a transformed posterior grid and a hierarchical MCMC fit with a distinct prior. All 71 original observed historical count pairs are preserved.",
        task_title="Compare grid and MCMC inference for rat-tumor experiments",
        review_description="Three scientific output tables and 19 passing controls. Native oracle/no-op/GLM rewards are 1/0/1. The prompts, inputs, outputs and attempt below belong to the same published task; this one example does not establish reliability across the ten-domain panel or universal implementation portability.",
        runtime_revision="19d3547a730af3e0724e18dd6aa3a7b33e84ab91",
        program_revisions={"release": "b1f1c4b8"},
        review_files=[
            "autonomous-runs/215/scientific-release-check.json",
            "autonomous-runs/215/hub-download-verification.json",
            "autonomous-runs/215/input-notice-review.json",
            "autonomous-runs/215/provider-cleanup.json",
            PREFIX + "grading/review.json",
            PREFIX + "grading/final-controls.json",
        ],
        trial_result="autonomous-runs/215/scientific-release-check.json",
        trial_result_label="Independent verification of the original native trials",
        release={
            "repository": publication["repo_id"],
            "publication": "autonomous-runs/215/publication.json",
        },
    )
    profile["notebook"] = PREFIX + "source.ipynb.gz"
    native = json.loads((ORIGINAL / "native/result.json").read_text())
    trajectory_path = Path("native") / native["solver"]["result_path"]
    trajectory_path = trajectory_path.parent / "agent/trajectory.json"
    profile["trajectory_glob"] = PREFIX + trajectory_path.as_posix()
    profile["verifier_report"] = (
        PREFIX + (trajectory_path.parent.parent / "verifier/report.json").as_posix()
    )
    manifest = json.loads((ARCHIVE / "sealed-manifest.json").read_text())
    rows = {row["path"]: row for row in manifest["files"]}
    selected, derived = {}, {}
    DEST.mkdir(parents=True)

    def original(name):
        raw = (ORIGINAL / name).read_bytes()
        row = rows[name]
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
        return raw

    def put(name, raw, provenance):
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == raw
        else:
            target.write_bytes(raw)
        selected[name] = {"sha256": sha(raw), "bytes": len(raw), **provenance}

    def copy_original(name):
        put(name, original(name), {"original_archive_path": name, "byte_preserved": True})

    def generated(name, text, inputs):
        raw = text.encode()
        put(name, raw, {"derived_display_document": True, "source_fields": inputs})
        derived[name] = inputs

    payload = BASE / "launch/215-payload"
    config = json.loads((payload / "campaign-config.json").read_text())
    with tarfile.open(payload / "biotasks.tar") as source:
        for target, key in [("source.ipynb", "notebook_file"), ("seed.json", "seed_file")]:
            name = "experiments/19-repo2rlenv-notebook-pilot/" + config[key]
            raw = source.extractfile(name).read()
            frozen = json.loads((EXP / "panel-rounds/108/freeze-215.json").read_text())
            assert sha(raw) == frozen["source_assets"][name]
            if target == "source.ipynb":
                compressed = gzip.compress(raw, mtime=0)
                assert gzip.decompress(compressed) == raw
                put(
                    target + ".gz",
                    compressed,
                    {
                        "frozen_original_source_asset": name,
                        "lossless_gzip": True,
                        "uncompressed_sha256": sha(raw),
                        "byte_preserved_after_decompression": True,
                    },
                )
            else:
                put(target, raw, {"frozen_original_source_asset": name, "byte_preserved": True})
    copy_original("native/tasks/autonomous-panel-215/environment/SOURCE-LICENSES.json")

    display_paths = {}

    def output_document(name, paths, role):
        text = [
            f"# {role}",
            "",
            "Original files; no values were recomputed for this viewer.",
            "",
            "| Output | Bytes | SHA256 |",
            "| --- | ---: | --- |",
        ]
        for path in paths:
            row = rows[path]
            exact_downloads = [
                name
                for name, item in rows.items()
                if name.startswith("native/tasks/autonomous-panel-215/tests/reference/")
                and item["sha256"] == row["sha256"]
                and item["bytes"] == row["bytes"]
            ]
            published_name = Path(exact_downloads[0]).name if exact_downloads else Path(path).name
            download = (
                f"https://huggingface.co/datasets/{publication['repo_id']}/resolve/"
                f"{publication['commit_sha']}/tasks/autonomous-panel-215/tests/reference/{published_name}"
            )
            native_path = "native/tasks/autonomous-panel-215/tests/reference/" + Path(path).name
            label = Path(path).name
            if exact_downloads:
                label = f"[{label}]({download})"
            else:
                label += " (original export shown in this stage; published representation differs)"
            text.append(f"| {label} | {row['bytes']} | `{row['sha256']}` |")
            if row["bytes"] > 1024 * 1024:
                assert exact_downloads, "Large display output needs an exact published download"
                preview_name = path + ".preview.md"
                preview = "\n".join(original(path).decode().splitlines()[:31])
                generated(
                    preview_name,
                    f"# {Path(path).name} — display preview\n\nFirst 30 data rows; values are not recomputed. [Download the complete original]({download}). Original size: {row['bytes']} bytes; SHA256 `{row['sha256']}`.\n\n```csv\n{preview}\n```\n",
                    [path],
                )
                display_paths[path] = preview_name
            else:
                copy_original(path)
                display_paths[path] = path
        generated(name, "\n".join(text) + "\n", paths)

    reference_paths = sorted(
        path
        for path in rows
        if path.startswith("reference/trial/outputs/") and path.endswith(".csv")
    )
    final_paths = sorted(
        path
        for path in rows
        if path.startswith("materialization/reference/") and path.endswith(".csv")
    )
    output_document("reference-output-downloads.md", reference_paths, "Initial append-only exports")
    output_document("output-artifacts.md", final_paths, "Final task outputs")
    # Initial exports can differ from later recovered endpoints. Only link a
    # published final file when its original bytes are actually identical.
    for path in final_paths:
        native_path = "native/tasks/autonomous-panel-215/tests/reference/" + Path(path).name
        assert rows[path]["sha256"] == rows[native_path]["sha256"]
    by_id = {stage[0]: stage for stage in profile["stages"]}
    by_id["materialize"][3] = (
        "Construct task inputs, reference outputs and an oracle from the accepted source-grounded specification, preserving the original execution evidence."
    )
    by_id["independent"][3] = (
        "A separate worker receives the question and inputs without private reference or oracle access. Shared model families and dependency stacks limit independence and do not establish universal portability."
    )
    by_id["native"][3] = (
        f"Run oracle, empty baseline and a blind GLM solver in offline CPU environments. Recorded rewards: {native['controls'][0]['reward']}/{native['controls'][1]['reward']}/{native['solver']['reward']}. Solver exception: {native['solver']['exception_type'] or 'none'}. All original trajectory steps are retained."
    )
    by_id["worker"][5] = [group for group in by_id["worker"][5] if group[0] != "Output artifacts"]
    by_id["worker"][5].append(
        [
            "Output artifacts",
            [
                [PREFIX + "reference/output-audit.json", "Original output inventory"],
                [
                    PREFIX + "reference-output-downloads.md",
                    "Original persisted exports and verified downloads",
                ],
            ]
            + [[PREFIX + display_paths[path], Path(path).name] for path in reference_paths],
        ]
    )
    by_id["materialize"][5] = [
        group for group in by_id["materialize"][5] if group[0] != "Reference outputs"
    ]
    by_id["materialize"][5].append(
        [
            "Reference outputs",
            [[PREFIX + "output-artifacts.md", "Final output inventory and downloads"]]
            + [[PREFIX + display_paths[path], Path(path).name] for path in final_paths],
        ]
    )
    initial = by_id["initial-review"]
    initial[5] = [
        group
        for group in initial[5]
        if group[0] not in {"Evidence available to the review tools", "Output"}
    ]
    initial[5].append(["Output", [[PREFIX + "grading/review.json", "Initial scientific review"]]])
    # This run has no quality repair; show only its actual review.
    for stage, input_name in [(initial, "grading/review/input.json")]:
        value = json.loads(original(input_name))
        descriptor = value.get("review_evidence", {})
        assert descriptor.get("context_sha256")
        packet_name = (
            "grading/review-inspection/review-packets/v1-"
            + descriptor["context_sha256"]
            + "/manifest.json"
        )
        packet = json.loads(original(packet_name))
        evidence = [[PREFIX + packet_name, "Complete identity-bound evidence index"]]
        for field, row in packet["fields"].items():
            path = str(Path(packet_name).parent / row["path"])
            assert rows[path]["sha256"] == row["sha256"]
            evidence.append([PREFIX + path, field])
        stage[5].insert(-1, ["Evidence available to the review tools", evidence])
    trajectory = json.loads(original(trajectory_path.as_posix()))
    assert trajectory["steps"][0]["source"] == "user"
    generated(
        "native/solver-input.md",
        trajectory["steps"][0]["message"],
        [trajectory_path.as_posix() + "#/steps/0/message"],
    )
    harness = {
        "agent": "terminus-2",
        "model": "glm-5.3",
        "solver_seconds": 600,
        "requested_effort": "high",
        "served_effort_verified": False,
        "connection_details_excluded": True,
        "source": "native/execution.json",
    }
    generated(
        "native/harness-summary.json",
        json.dumps(harness, indent=2) + "\n",
        ["native/execution.json", "pipeline.json"],
    )
    for name in ["manifest.json", "release-files.json"]:
        raw = (BASE / "release215/anonymous-download" / name).read_bytes()
        put(
            "release/" + name,
            raw,
            {"verified_publication_revision": publication["commit_sha"], "byte_preserved": True},
        )
    for number, stage in enumerate(profile["stages"], 1):
        label = stage[1].split(" · ", 1)[-1]
        stage[1] = f"{number:02} · {label}"

    def collect(value):
        if isinstance(value, str) and value.startswith(PREFIX):
            name = value.removeprefix(PREFIX)
            if name not in selected:
                copy_original(name)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)

    collect(profile)
    # Existing selected artifacts must not leak private service configuration.
    for name in selected:
        raw = (DEST / name).read_bytes()
        assert b"/muchanem/" not in raw and b"glm53-relay" not in raw, name
    (DEST / "NOTICE.md").write_text(
        "# Source notices\n\nThe original PyMC source notebook and captured scientific source retain the MIT notice and original BDA3 attribution in `native/tasks/autonomous-panel-215/environment/SOURCE-LICENSES.json`. See the published exact-input notice review. Generated task evidence is reproduced unchanged; no source asset is relicensed by this viewer.\n"
    )
    (PUBLIC / "selected-evidence.json").write_text(
        json.dumps(
            {
                "campaign": 215,
                "original_archive_manifest_sha256": sha(
                    (ARCHIVE / "sealed-manifest.json").read_bytes()
                ),
                "files": selected,
                "derived_display_documents": derived,
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
                "stages": len(profile["stages"]),
                "selected_files": len(selected),
                "solver_steps": len(trajectory["steps"]),
                "current_example": 215,
            }
        )
    )


if __name__ == "__main__":
    main()
