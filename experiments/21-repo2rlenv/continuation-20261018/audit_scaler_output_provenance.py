"""Read-only lineage check of native expansion from a supplied Scaler family.

No generated program, reference solution, task grader or model is executed.
"""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(archive, campaign, queue):
    manifest_path = ROOT / "hf-scaler-dna-01-snapshot-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    original = next(row for row in manifest["files"] if row["path"].endswith("native-evidence.tar.gz"))
    assert archive.stat().st_size == original["bytes"] and digest(archive) == original["sha256"]
    family = ROOT / "seeds/scaler-dna-edit-v1/families.json"
    family_hash = digest(family)
    assert family_hash == next(row["sha256"] for row in manifest["files"]
                               if row["path"] == "seeds/scaler-dna-edit-v1/families.json")
    source_profile = json.loads((ROOT / "scaler-dna-profile.json").read_text())
    assert source_profile["source_sha256"] == family_hash
    actual_members = []
    task_members = {}
    generation = None
    with tarfile.open(archive, "r|gz") as tar:
        total = 0
        for member in tar:
            if member.isdir():
                continue
            assert member.isfile() and member.size < 1024**2
            total += member.size
            assert total < 32 * 1024**2
            data = tar.extractfile(member).read()
            record = {"path":member.name, "bytes":member.size,
                      "mode":oct(member.mode & 0o7777), "sha256":hashlib.sha256(data).hexdigest()}
            actual_members.append(record)
            if member.name == "native/runs/scaler-dna-01/scaler-dna-01/generation.json":
                generation = json.loads(data)
            if member.name.startswith("native/tasks/"):
                name, relative = member.name.removeprefix("native/tasks/").split("/", 1)
                task_members.setdefault(name, {})[relative] = record
    assert actual_members == original["members"]
    assert generation is not None
    admissions = json.loads((ROOT / "evidence/scaler-native-acceptance/summary.json").read_text())
    assert set(task_members) == {row["task"] for row in admissions["tasks"]}
    rows = []
    for admission in admissions["tasks"]:
        name = admission["task"]
        accepted = json.loads((ROOT / "evidence/scaler-native-acceptance" / (name + ".json")).read_text())
        assert accepted["native_original_bundle_accepted"]
        records = task_members[name]
        assert {key:value["sha256"] for key, value in records.items()} == accepted["asset_sha256"]
        assert {str(path.relative_to(queue / name / "roundtrip/task"))
                for path in (queue / name / "roundtrip/task").rglob("*") if path.is_file()} == set(records)
        for relative, original_file in records.items():
            for directory in (campaign / "tasks" / name, queue / name / "roundtrip/task"):
                path = directory / relative
                assert path.is_file() and not path.is_symlink()
                assert digest(path) == original_file["sha256"]
                assert oct(path.stat().st_mode & 0o7777) == original_file["mode"]
        candidate = next(row for row in generation["candidates"] if row["id"] == name.removeprefix("scaler-"))
        assert candidate["source_sha256"] == family_hash
        assert (campaign / "tasks" / name / "instruction.md").read_text() == candidate["instruction"]
        rows.append({"task_id":admission["task_id"], "native_task":name,
            "native_original_asset_count":len(records), "native_original_hashes_and_modes_preserved":True,
            "accepted_and_blind_input_assets_match":True,
            "family_source_sha256":family_hash,
            "category":"programmatic_output_unchanged_from_supplied_family",
            "task_specific_output_fixes":0, "native_bundle_hash":accepted["bundle_hash"]})
    return {"stage":"post_run_read_only_Scaler_output_lineage_assessment",
        "model_calls":0, "new_task_attempts":0, "generated_code_executed":False,
        "unchanged_native_expansions":len(rows), "independent_supplied_families":1,
        "source_archive_sha256":original["sha256"], "source_manifest_sha256":digest(manifest_path),
        "source_snapshot":"research/21-repo2rlenv/2026-10-17/afb5a91ef2e43d21e407db86d1f3c9be410bc4d0c1925e82123a35b804556450",
        "family_source_sha256":family_hash,
        "input_family_origin":"Codex prepared the family description, generator and reference before native instance expansion; synthetic strings, not observed biology.",
        "finding":"Native programmatic instance expansion from the declared supplied family is verified with no output repair. Prior unresolved classification is resolved for these instance assets, not for automatic family invention.",
        "limitations":["One supplied human-authored algorithm family, not three independent scientific competencies.",
            "No evidence of automatic scientific-family invention or its scalability.",
            "Manual final assessment and separate diagnostic controls remain disclosed.",
            "Existing blind scores unchanged; Marin score-bound mismatch remains unresolved."],
        "rows":rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("archive", "campaign", "queue", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.archive, args.campaign, args.queue)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unchanged_programmatic_instances":len(result["rows"]),
        "verified_task_assets":sum(row["native_original_asset_count"] for row in result["rows"]),
        "model_calls":0, "task_fixes":0, "automatic_family_invention_established":False}))
