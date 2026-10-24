"""Policy boundaries and shell-level failure propagation, without real APT."""

import importlib.util
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "index_policy", Path(__file__).with_name("index_policy.py")
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
MARKER, UnsupportedRecipe, emitter, normalize = (
    policy.MARKER,
    policy.UnsupportedRecipe,
    policy.emitter,
    policy.normalize,
)


@pytest.mark.parametrize(
    "command",
    [
        "apt-get -q install pkg",
        "apt install pkg",
        "apt-get install $PKG",
        "apt-get install pkg; true",
        "apt-get install pkg | tail -5",
        "apt-get install pkg || true",
        "apt-get install $(echo pkg)",
        "apt-get install pkg\ntrue",
        "apt-get install --allow-unauthenticated pkg",
        "apt-get install",
        "sudo apt-get install pkg",
        "echo apt-get install pkg",
    ],
)
def test_ambiguous_apt_is_explicitly_unsupported(command):
    with pytest.raises(UnsupportedRecipe):
        normalize(command)


def test_non_apt_and_already_refreshed_commands_preserved():
    for command in [
        "pip install -e '/workspace/.[development]'",
        "apk add --no-cache git",
        "apt-get update -q && apt-get install -y libexample-dev",
        "apt-get update -q",
    ]:
        assert normalize(command) == command


def test_emitter_restores_on_failure_and_preserves_saved_data():
    def original(owner, name, data):
        return "\n".join(data["rebuild_cmds"]) + "\n"

    native = SimpleNamespace(_build_clean_recipe=original)
    data = {"rebuild_cmds": ["apt-get install -y libexample-dev"], "ref": "unchanged"}
    before = deepcopy(data)
    with pytest.raises(RuntimeError), emitter(native) as changes:
        recipe = native._build_clean_recipe("some", "repo", data)
        assert recipe.startswith(MARKER)
        assert changes[0]["commands"][0][0] == data["rebuild_cmds"][0]
        raise RuntimeError("interrupted local export")
    assert native._build_clean_recipe is original
    assert data == before


def test_no_apt_emitter_is_byte_identical():
    native = SimpleNamespace(_build_clean_recipe=lambda *a: "original bytes\n")
    with emitter(native) as changes:
        assert (
            native._build_clean_recipe("a", "b", {"rebuild_cmds": ["pip install x"]})
            == "original bytes\n"
        )
        assert changes == []


@pytest.fixture
def apt(tmp_path):
    executable = tmp_path / "apt-get"
    executable.write_text(
        """#!/bin/sh
printf '%s\\n' "$*" >> "$APT_LOG"
case "$1" in
 update) [ "${APT_FAIL_UPDATE:-0}" = 0 ] || exit 7; touch "$APT_STATE";;
 install) [ -e "$APT_STATE" ] || exit 100;;
 *) exit 9;;
esac
"""
    )
    executable.chmod(0o755)
    return {
        "PATH": str(tmp_path) + ":/usr/bin:/bin",
        "APT_LOG": str(tmp_path / "calls"),
        "APT_STATE": str(tmp_path / "indexes"),
    }


def test_missing_index_baseline_and_candidate_shell_semantics(apt):
    original = "apt-get install -y libexample-dev"
    baseline = subprocess.run(["sh", "-c", original], env=apt, check=False)
    assert baseline.returncode == 100
    candidate = subprocess.run(["sh", "-c", normalize(original)], env=apt, check=False)
    assert candidate.returncode == 0
    assert Path(apt["APT_LOG"]).read_text().splitlines() == [
        "install -y libexample-dev",
        "update",
        "install -y libexample-dev",
    ]


def test_failed_refresh_does_not_run_install(apt):
    result = subprocess.run(
        ["sh", "-c", normalize("apt-get install -y package=1.2-3")],
        env={**apt, "APT_FAIL_UPDATE": "1"},
        check=False,
    )
    assert result.returncode == 7
    assert Path(apt["APT_LOG"]).read_text().splitlines() == ["update"]
