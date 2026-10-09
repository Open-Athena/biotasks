import hashlib

import pytest

from biotasks.factory_stage import stage_spec
from biotasks.prompts import load_prompt


@pytest.mark.parametrize("stage", ["authoring", "review", "repair"])
def test_worker_spec_binds_prompt_and_input_bytes(tmp_path, stage):
    archive = tmp_path / "inputs.zip"
    archive.write_bytes(b"candidate version one")
    first = stage_spec(stage, archive, 40, 1200)
    assert first["prompt"] == load_prompt(first["prompt_name"])
    assert first["prompt_sha256"] == hashlib.sha256(first["prompt"].encode()).hexdigest()
    archive.write_bytes(b"candidate version two")
    second = stage_spec(stage, archive, 40, 1200)
    assert first["input_zip_sha256"] != second["input_zip_sha256"]
    assert first["prompt"] == second["prompt"]


@pytest.mark.parametrize("requests,seconds", [(0, 1200), (41, 1200), (40, 1201)])
def test_stage_cannot_expand_session_budget(tmp_path, requests, seconds):
    with pytest.raises(ValueError, match="limits"):
        stage_spec("repair", tmp_path / "absent.zip", requests, seconds)
