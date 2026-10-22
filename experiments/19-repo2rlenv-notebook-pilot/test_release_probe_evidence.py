"""Release evidence must describe the exact probes executed after repair."""

import json

import pytest
from grading_protocol import Grader, GraderRepair, Probes, apply_probe_expectations
from release_metadata import scientific_probe_documents


def fixture(tmp_path, *, repaired=True, concerns_update=None):
    candidate = Grader(
        disposition="ready",
        instruction="Return the correct scalar and retain the schema.",
        grader_code="pass",
        rationale="Synthetic evidence fixture",
        checks=[
            {"id": name, "kind": kind, "artifacts": ["value.txt"], "public_requirement": name}
            for name, kind in [("value", "scientific"), ("schema", "structural")]
        ],
    )
    fields = dict(
        focus="general",
        rationale="Synthetic mutation",
        evidence=[{"path": "instruction.md", "quote": "scalar"}],
        script="from pathlib import Path\nPath('value.txt').write_text('2')",
    )
    original = Probes(
        disposition="ready",
        concerns=[] if concerns_update is None else ["An earlier unverified observation."],
        probes=[
            {
                **fields,
                "name": "value-edit",
                "kind": "wrong_solution",
                "check_ids": ["value", "schema"],
            },
            {
                **fields,
                "name": "format",
                "kind": "valid_alternative",
                "check_ids": ["schema"],
                "script": "from pathlib import Path\nPath('value.txt').write_text('1.0')",
            },
        ],
    )
    suite = original

    def save(name, value):
        (tmp_path / name).write_text(json.dumps(value))

    save("probes.json", original.model_dump())
    if repaired:
        repair = GraderRepair(
            **candidate.model_dump(),
            probe_concerns=concerns_update,
            probe_expectations=[
                {
                    "name": "value-edit",
                    "check_ids": ["value"],
                    "rationale": "The scalar changes while the schema is retained.",
                }
            ],
        )
        _, suite = apply_probe_expectations(repair, original)
        save("repair.json", repair.model_dump())
        save("repaired-probes.json", suite.model_dump())
    save("final-candidate.json", candidate.model_dump())
    save("final-controls.json", [{"kind": "probe", "probe": p.model_dump()} for p in suite.probes])
    return original, suite


def test_legacy_suite_is_preserved(tmp_path):
    original, _ = fixture(tmp_path, repaired=False)
    assert scientific_probe_documents(tmp_path) == {"scientific-probes.json": original.model_dump()}


def test_effective_suite_and_original_annotations_are_both_published(tmp_path):
    original, suite = fixture(tmp_path)
    docs = scientific_probe_documents(tmp_path)
    assert docs["scientific-probes.json"] == suite.model_dump()
    assert docs["initial-scientific-probes.json"] == original.model_dump()
    assert docs["probe-expectation-corrections.json"]["mutation_scripts_unchanged"] is True


def test_corrected_suite_concerns_are_published_with_the_original(tmp_path):
    original, suite = fixture(
        tmp_path, concerns_update=["Correction supported by controller evidence."]
    )
    docs = scientific_probe_documents(tmp_path)
    assert docs["scientific-probes.json"]["concerns"] == suite.concerns
    assert docs["initial-scientific-probes.json"]["concerns"] == original.concerns
    assert docs["probe-expectation-corrections.json"]["suite_concerns"] == {
        "original": original.concerns,
        "revised": suite.concerns,
    }


@pytest.mark.parametrize(
    "defect",
    [
        "stale-controls",
        "changed-script",
        "missing-control",
        "duplicate-control",
        "missing-repair",
        "changed-grader",
        "changed-concerns",
    ],
)
def test_mismatched_or_incomplete_evidence_blocks_release(tmp_path, defect):
    original, suite = fixture(tmp_path)

    def read(name):
        return json.loads((tmp_path / name).read_text())

    def save(name, value):
        (tmp_path / name).write_text(json.dumps(value))

    if defect == "stale-controls":
        save(
            "final-controls.json",
            [{"kind": "probe", "probe": p.model_dump()} for p in original.probes],
        )
    elif defect == "changed-script":
        value = suite.model_dump()
        value["probes"][0]["script"] = "print('changed mutation')"
        save("repaired-probes.json", value)
    elif defect == "missing-control":
        save("final-controls.json", read("final-controls.json")[:1])
    elif defect == "duplicate-control":
        save("final-controls.json", read("final-controls.json") * 2)
    elif defect == "missing-repair":
        (tmp_path / "repair.json").unlink()
    elif defect == "changed-concerns":
        value = suite.model_dump()
        value["concerns"] = ["Unrecorded modification"]
        save("repaired-probes.json", value)
    else:
        value = read("final-candidate.json")
        value["grader_code"] = "print('different grader')"
        save("final-candidate.json", value)
    with pytest.raises(ValueError):
        scientific_probe_documents(tmp_path)
