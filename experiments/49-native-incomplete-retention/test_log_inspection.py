"""Negative archival-policy checks, without modifying or accepting raw grades."""

import importlib.util
from pathlib import Path

import pytest
from biotasks.validation import preservation
from biotasks.validation.files import ValidationError

spec = importlib.util.spec_from_file_location(
    "log_inspection", Path(__file__).with_name("log_inspection.py")
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
TASK = "org__repo-12"
NAME = "jobs/" + TASK + "-oracle/" + TASK + "__abc/verifier/test_output.log"


def test_original_bytes_preserved_and_context_restored():
    raw = b"test_a PASSED\n\0\0test_b FAILED\n"
    row = policy.review(TASK, NAME, raw)
    original = preservation.inspect
    with pytest.raises(RuntimeError), policy.reviewed_native_logs(TASK, [row]):
        preservation.inspect(raw, NAME)
        assert raw.count(b"\0") == 2
        raise RuntimeError("interrupted upload")
    assert preservation.inspect is original
    with pytest.raises(ValidationError):
        preservation.inspect(raw, NAME)


def test_unknown_binary_path_is_rejected():
    raw = b"text\0text"
    row = policy.review(TASK, NAME, raw)
    with policy.reviewed_native_logs(TASK, [row]), pytest.raises(ValidationError):
        preservation.inspect(raw, "outputs/task/unknown.bin")


def test_changed_reviewed_bytes_are_rejected():
    raw = b"text\0text"
    row = policy.review(TASK, NAME, raw)
    with policy.reviewed_native_logs(TASK, [row]), pytest.raises(ValidationError):
        preservation.inspect(raw + b"changed", NAME)


def test_secret_shape_split_by_padding_is_still_rejected():
    token = b"gh" + b"p_" + b"a" * 32
    raw = token[:8] + b"\0" + token[8:]
    with pytest.raises(ValidationError):
        policy.review(TASK, NAME, raw)


def test_invalid_utf8_remains_rejected():
    with pytest.raises(ValidationError):
        policy.review(TASK, NAME, b"\xff\0text")


def test_binary_control_bytes_remain_rejected():
    with pytest.raises(ValidationError):
        policy.review(TASK, NAME, b"text\x03\0text")


def test_exception_cannot_cover_task_assets_or_other_agents():
    with pytest.raises(ValidationError):
        policy.review(TASK, "outputs/task/tests/verifier.py", b"text\0text")
    with pytest.raises(ValidationError):
        policy.review(TASK, NAME.replace("-oracle/", "-solver/"), b"text\0text")
