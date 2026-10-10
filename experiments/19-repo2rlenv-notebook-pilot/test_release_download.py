"""A Hub-style download must preserve identity despite losing executable bits."""

import shutil

import pytest
from repo2rlenv.campaigns.release import ReleasePlan, ReleaseTask, stage_release
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, inspect_bundle, write_bundle
from verify_hub_download import check_download


def staged_fixture(tmp_path):
    task = write_bundle(
        TaskBundle(
            name="transport-fixture",
            org="tests",
            instruction="Transport fixture only; not a scientific task.",
            files={
                "environment/Dockerfile": TaskFile.text("FROM python:3.13-slim\n"),
                "solution/solve.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
                "tests/test.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
            },
            metadata={"recipe": "fixture", "recipe_version": "1", "reward_kinds": ["binary"]},
        ),
        tmp_path / "original",
    )
    stage = tmp_path / "staged"
    stage_release(
        ReleasePlan(
            repo_id="tests/fixture",
            recipe="fixture",
            title="Transport fixture",
            description="Local-only fixture",
            methodology="No execution",
            code_revision="a" * 40,
            tasks=[ReleaseTask(path=task, bundle_hash=inspect_bundle(task)["bundle_hash"])],
        ),
        stage,
    )
    return task, stage


def test_archive_restores_executable_modes_and_original_bundle(tmp_path):
    task, stage = staged_fixture(tmp_path)
    cache = tmp_path / "hub-cache"
    shutil.copytree(stage, cache)
    for path in cache.rglob("*"):
        if path.is_file():
            path.chmod(0o644)
    fetched = []

    def download(name):
        fetched.append(name)
        return cache / name

    target = tmp_path / "download"
    result = check_download("tests/fixture", "a" * 40, target, download)
    restored = target / "tasks" / task.name
    assert (restored / "solution/solve.sh").stat().st_mode & 0o777 == 0o755
    assert inspect_bundle(restored) == inspect_bundle(task)
    assert result["verified"]
    assert not any(name.startswith("tasks/") for name in fetched)


def test_corrupted_archive_is_rejected_before_extraction(tmp_path):
    _, stage = staged_fixture(tmp_path)
    archive = stage / "tasks.tar.gz"
    original = archive.read_bytes()
    archive.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    target = tmp_path / "download"
    with pytest.raises(ValueError, match="Downloaded bytes changed"):
        check_download("tests/fixture", "a" * 40, target, lambda name: stage / name)
    assert not (target / "tasks").exists()
