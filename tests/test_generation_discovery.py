"""Official discovery adapter forwarding and frozen resume; no GitHub calls."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from biotasks.generation import discovery
from biotasks.validation.files import ValidationError, read_json, write_json


@pytest.fixture
def listing(tmp_path, monkeypatch):
    @dataclass
    class PR:
        number: int
        state: str

    cache = tmp_path / "cache"
    cache.mkdir()
    write_json(cache / "receipt.json", {"synthetic": True})
    monkeypatch.setattr(discovery.source, "verify", lambda root: {"synthetic": True})
    config = tmp_path / "native.json"
    write_json(
        config,
        {
            "repo": {"url": "https://github.com/synthetic/repo", "access": "public"},
            "pipeline": {
                "name": "pr_runtime",
                "options": {"limit": 2, "since": "2026-10-12", "until": "2026-10-12"},
            },
        },
    )
    calls = []

    def native(*args, **kwargs):
        calls.append((args, kwargs))
        return [PR(1, "MERGED"), PR(2, "MERGED")]

    module = SimpleNamespace(
        __file__=str(cache / "source/src/repo2rlenv/github.py"), list_merged_prs=native
    )
    original_import = discovery.importlib.import_module

    def import_native(name, package=None):
        if name == "repo2rlenv.github":
            return module
        return original_import(name, package)

    monkeypatch.setattr(discovery.importlib, "import_module", import_native)
    return config, cache, tmp_path / "prs.json", calls


def test_forwards_official_options_once_and_reuses_completed_snapshot(listing):
    config, cache, output, calls = listing
    result = discovery.freeze(config, cache, output)
    assert result["candidates"] == [
        {"number": 1, "state": "MERGED"},
        {"number": 2, "state": "MERGED"},
    ]
    assert calls[0][0] == ("synthetic", "repo") and calls[0][1]["limit"] == 2
    assert calls[0][1]["since"].isoformat() == "2026-10-12"
    assert discovery.freeze(config, cache, output) == result and len(calls) == 1


def test_changed_completed_snapshot_does_not_trigger_another_listing(listing):
    config, cache, output, calls = listing
    discovery.freeze(config, cache, output)
    result = read_json(output)
    result["candidates"] = []
    write_json(output, result)
    with pytest.raises(ValidationError, match="snapshot changed"):
        discovery.freeze(config, cache, output)
    assert len(calls) == 1


def test_overwide_discovery_rejected_before_native_call(listing):
    config, cache, output, calls = listing
    value = read_json(config)
    value["pipeline"]["options"]["limit"] = 101
    write_json(config, value)
    with pytest.raises(ValidationError, match="Discovery bound"):
        discovery.freeze(config, cache, output)
    assert not calls


@pytest.mark.parametrize("setting", [False, True])
def test_optional_official_filter_is_frozen_without_becoming_listing_argument(listing, setting):
    config, cache, output, calls = listing
    value = read_json(config)
    value["pipeline"]["options"]["require_new_test_funcs"] = setting
    write_json(config, value)
    result = discovery.freeze(config, cache, output)
    assert result["require_new_test_funcs"] is setting
    assert set(calls[0][1]) == {"limit", "since", "until"}
    assert discovery.freeze(config, cache, output) == result and len(calls) == 1


@pytest.mark.parametrize("setting", [0, 1, "false", None])
def test_non_boolean_official_filter_rejected_before_discovery(listing, setting):
    config, cache, output, calls = listing
    value = read_json(config)
    value["pipeline"]["options"]["require_new_test_funcs"] = setting
    write_json(config, value)
    with pytest.raises(ValidationError, match="Discovery bound"):
        discovery.freeze(config, cache, output)
    assert not calls
