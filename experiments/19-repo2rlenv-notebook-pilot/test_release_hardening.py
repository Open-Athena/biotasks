"""Reject malformed evidence and oversized archive metadata before extraction."""

import gzip
import json
import tarfile

import pytest
from reconstruct_release_label import local, reconstruct
from verify_hub_download import bounded_archive


@pytest.mark.parametrize(
    "value", ["/evidence/../../outside", "/evidence//outside", "/evidence/a/../outside"]
)
def test_traversal_leaves_external_file_untouched(tmp_path, value):
    source = tmp_path / "source"
    folder = source / "pilot/quality"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps({"task_path": value, "trials": []}))
    outside = tmp_path / "outside"
    outside.write_text("preserve")
    with pytest.raises(ValueError):
        reconstruct(source, tmp_path / "copy")
    assert outside.read_text() == "preserve"
    assert not (tmp_path / "copy").exists()


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        local(root, "/evidence/escape/file")


def test_unlisted_directory_rejected_before_extraction(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as out:
        member = tarfile.TarInfo("tasks/unlisted")
        member.type = tarfile.DIRTYPE
        out.addfile(member)
    destination = tmp_path / "download"
    destination.mkdir()
    with pytest.raises(ValueError, match="Unexpected archive directory"):
        bounded_archive(archive, destination, {})
    assert not list(destination.iterdir())


def test_metadata_expansion_rejected_before_parsing(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    header = tarfile.TarInfo("pax")
    header.type = tarfile.XHDTYPE
    header.size = 1024 * 1024
    with gzip.open(archive, "wb") as out:
        out.write(header.tobuf())
    destination = tmp_path / "download"
    destination.mkdir()
    with pytest.raises(ValueError, match="metadata exceeds"):
        bounded_archive(archive, destination, {})
    assert not list(destination.iterdir())


def test_real_sdk_folder_upload_routes_serial_setting_to_commit(tmp_path, monkeypatch):
    """Exercise the installed folder API; it rejects num_threads on that method."""
    import inspect

    import huggingface_hub.hf_api as sdk
    from publish_scientific_release import SerialHfApi

    signature = inspect.signature(sdk.HfApi.create_commit)
    calls = []
    sentinel = object()

    def commit(self, *args, **kwargs):
        signature.bind(self, *args, **kwargs)
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(sdk.HfApi, "create_commit", commit)
    monkeypatch.setattr(sdk, "is_xet_available", lambda: False)
    (tmp_path / "artifact.txt").write_text("fixture")
    api = SerialHfApi(token=False)
    assert (
        api.upload_folder(
            repo_id="owner/release",
            repo_type="dataset",
            folder_path=tmp_path,
            parent_commit="a" * 40,
            commit_message="fixture",
        )
        is sentinel
    )
    assert len(calls) == 1 and calls[0]["num_threads"] == 1
    assert calls[0]["parent_commit"] == "a" * 40
    assert [op.path_in_repo for op in calls[0]["operations"]] == ["artifact.txt"]
