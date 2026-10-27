import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "snapshot_origin_fixture", Path(__file__).with_name("snapshot_origin.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PREFIX = "s3://marin-us-east-02a/marin/evals/biotasks19/20261026-panel103/biotasks19-autonomous-panel-210/"


def test_explicit_successor_and_original_default():
    assert module.campaign_prefix(210, PREFIX) == PREFIX
    assert "panel101" in module.campaign_prefix(197)


@pytest.mark.parametrize(
    "value",
    [
        None,
        PREFIX.replace("210", "211"),
        PREFIX + "autonomous-snapshot/",
        PREFIX.replace("marin-us-east-02a", "elsewhere"),
        PREFIX.replace("/20261026-", "/../20261026-"),
        PREFIX.rstrip("/"),
        PREFIX + "?query=1",
    ],
)
def test_mismatched_or_guessed_source_refused(value):
    with pytest.raises(ValueError):
        module.campaign_prefix(210, value)
