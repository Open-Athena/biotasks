"""Cache identity is generic and unique; original mixed-case input is retained."""

from types import SimpleNamespace

import pytest

from biotasks.generation.handoff import cache_bindings
from biotasks.validation.files import ValidationError, inventory, write_json


@pytest.fixture
def cache(tmp_path):
    root = tmp_path / "cache"
    slot = root / "OwNeR__MiXeD" / ("a" * 12 + "__options")
    slot.mkdir(parents=True)
    image = "local/r2e-bootstrap/owner__mixed:" + "a" * 12
    saved = {
        "repo": "OwNeR/MiXeD",
        "ref": "a" * 40,
        "image_tag": image,
        "rebuild_cmds": ["python -m pip install -e ."],
    }
    write_json(slot / "bootstrap.json", saved)
    native = SimpleNamespace(
        _list_task_dirs=lambda raw: [raw / "task"],
        _bootstrap_image_refs=lambda tasks: [(image, tasks[0])],
        _parse_local_tag=lambda ref: ("owner", "mixed", "a" * 12),
    )
    return root, slot, native, saved


def test_mixed_case_has_one_binding_without_mutating_cache(cache, tmp_path):
    root, slot, native, _ = cache
    before = inventory(root)
    _, bindings = cache_bindings(native, tmp_path / "raw", root)
    assert bindings[0]["cache"] == slot.relative_to(root).as_posix() + "/bootstrap.json"
    assert bindings[0]["repo"] == "OwNeR/MiXeD" and bindings[0]["staging_root"] == "owner__mixed"
    assert inventory(root) == before


@pytest.mark.parametrize(
    "kind",
    ["collision", "root-link", "slot-link", "record-link", "repository", "image", "ref", "missing"],
)
def test_ambiguous_unsafe_or_changed_identities_fail(cache, tmp_path, kind):
    root, slot, native, saved = cache
    if kind == "collision":
        (root / "owner__mixed").mkdir()
    elif kind == "root-link":
        slot.parent.rename(tmp_path / "outside")
        (root / "OwNeR__MiXeD").symlink_to(tmp_path / "outside", target_is_directory=True)
    elif kind == "slot-link":
        slot.rename(tmp_path / "outside")
        slot.symlink_to(tmp_path / "outside", target_is_directory=True)
    elif kind == "record-link":
        (slot / "bootstrap.json").rename(tmp_path / "record.json")
        (slot / "bootstrap.json").symlink_to(tmp_path / "record.json")
    elif kind == "missing":
        (slot / "bootstrap.json").unlink()
    else:
        saved[{"repository": "repo", "image": "image_tag", "ref": "ref"}[kind]] = {
            "repository": "owner/foreign",
            "image": "local/r2e-bootstrap/owner__foreign:" + "a" * 12,
            "ref": "b" * 40,
        }[kind]
        write_json(slot / "bootstrap.json", saved)
    with pytest.raises(ValidationError):
        cache_bindings(native, tmp_path / "raw", root)
