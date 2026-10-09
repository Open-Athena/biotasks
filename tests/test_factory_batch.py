import hashlib
import json

import pytest

from biotasks.factory_batch import freeze_batch


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
