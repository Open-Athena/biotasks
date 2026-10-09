import hashlib
import json

import pytest

from biotasks.factory_batch import execution_limits, freeze_batch


def test_arbitrary_panel_uses_one_frozen_prompt_and_preserves_all_inputs(tmp_path):
    inputs = {}
    for name in ["arbitrary-alpha", "arbitrary-beta", "arbitrary-gamma"]:
        path = tmp_path / name
        path.write_bytes(name.encode())
        inputs[name] = path
    output = tmp_path / "batch.json"
    receipt = freeze_batch("a" * 40, inputs, {"solver_seconds": 300}, 40, 1200, 2, output)
    record = json.loads(output.read_text())
    assert receipt["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert record["seed_count"] == 3
    assert set(record["entries"]) == set(inputs)
    assert len({spec["prompt_sha256"] for spec in record["entries"].values()}) == 1
    assert len({spec["input_zip_sha256"] for spec in record["entries"].values()}) == 3
    with pytest.raises(FileExistsError):
        freeze_batch("a" * 40, inputs, {}, 40, 1200, 2, output)


def test_execution_budget_must_be_frozen_and_respected(tmp_path):
    limits = {
        "concurrency": 1,
        "seeds_per_batch": 1,
        "resources": {"cpus": 4},
        "maximum_model_requests_per_session": 40,
        "maximum_output_tokens_per_request": 16384,
        "session_wall_seconds": 1200,
    }
    budget = tmp_path / "budget.json"
    budget.write_text(json.dumps(limits))
    archive = tmp_path / "inputs.zip"
    archive.write_bytes(b"input")
    output = tmp_path / "batch.json"
    freeze_batch(
        "a" * 40,
        {"unseen": archive},
        {"resources": {"cpus": 4}},
        40,
        1200,
        1,
        output,
        execution_budget=budget,
    )
    batch = json.loads(output.read_text())
    assert execution_limits(batch, budget.read_bytes()) == limits
    with pytest.raises(ValueError, match="not bound"):
        execution_limits(batch, b"{}")
    batch["entries"]["unseen"]["output_cap"] = 20000
    with pytest.raises(ValueError, match="output_cap"):
        execution_limits(batch, budget.read_bytes())
