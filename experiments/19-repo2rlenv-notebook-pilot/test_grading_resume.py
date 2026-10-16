"""Recovery rejects changed science or bytes before executing saved worker code."""

import hashlib
import json

import pytest
from grading_resume import load_resume
from test_grading import candidate


def fixture(root):
    context = {"paths": {"reference_outputs": "/reference"}, "question": "synthetic"}
    saved = context | {
        "paths": context["paths"] | {"independent_outputs": "/alternative"},
        "independent_solution": {},
        "independent_execution": {},
    }
    values = {
        "result.json": {"cleanup_verified": True, "status": "incomplete"},
        "grader/input.json": saved,
        "independent-solution.json": {
            "disposition": "ready",
            "code": "pass",
            "rationale": "fixture",
        },
        "candidate.json": candidate().model_dump(),
    }
    records = []
    for name, value in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value).encode()
        path.write_bytes(data)
        records.append(
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    (root / "artifact-manifest.json").write_text(
        json.dumps({"download_checked": True, "original_small_files": records})
    )
    return context


def test_resume_returns_original_code_and_rejects_changed_inputs(tmp_path):
    context = fixture(tmp_path)
    independent, grader = load_resume(tmp_path, context)
    assert independent.code == "pass"
    assert grader == candidate()
    with pytest.raises(ValueError, match="context differs"):
        load_resume(tmp_path, context | {"question": "changed"})
    (tmp_path / "candidate.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_resume(tmp_path, context)


def test_resume_requires_verified_download(tmp_path):
    context = fixture(tmp_path)
    p = tmp_path / "artifact-manifest.json"
    value = json.loads(p.read_text())
    value["download_checked"] = False
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="download-verified"):
        load_resume(tmp_path, context)
