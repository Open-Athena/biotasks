"""Watch scheduling never replaces native readiness or fixed-handle gates."""

import json

import pytest

from biotasks.generation import cli, scheduling
from biotasks.retention import actor
from biotasks.validation.files import write_json
from biotasks.validation.journal import STAGES


@pytest.mark.parametrize(
    ("state", "marker", "expect_wait"),
    [
        ("performed:candidate_verified", True, False),
        ("candidate_verified", True, False),
        ("recovering:submission_recorded", False, True),
        ("recovering:submission_recorded", True, False),
        ("performed:remote_terminal", False, True),
        ("performed:archive_readback_verified", True, False),
        ("recovering:cleanup_terminal", False, True),
        ("recovering:cleanup_terminal", True, False),
        ("performed:source_verified", True, False),
        ("pending:cleanup_terminal:handle_missing", True, True),
        ("performed:submission_recorded:unknown", True, True),
        ("performed:../../foreign", True, True),
    ],
)
def test_ready_evidence_drains_but_pending_or_unknown_states_keep_poll_interval(
    tmp_path, state, marker, expect_wait
):
    if marker:
        # Only legitimate marker names exist; foreign/unknown strings cannot
        # select paths outside the actual finite stage vocabulary.
        for stage in set(STAGES) | set(actor.STAGES):
            write_json(tmp_path / (stage + ".json"), {"stage": stage})
    assert (
        scheduling.waiting(tmp_path, state, tuple(set(STAGES) | set(actor.STAGES))) is expect_wait
    )


@pytest.fixture
def watch(tmp_path, monkeypatch):
    write_json(
        tmp_path / "manifest-plan.json", {"binding": {"manifest": str(tmp_path / "input.json")}}
    )
    sleeps, calls = [], []
    monkeypatch.setattr(cli.time, "sleep", sleeps.append)

    def prepare(values):
        sequence = iter(values)

        def advance(manifest, output, **flags):
            calls.append((manifest, output, flags))
            return next(sequence)

        monkeypatch.setattr(cli.planning, "advance", advance)

    return tmp_path, prepare, sleeps, calls


def test_watch_drains_ready_generation_native_and_retention_without_idle_passes(watch, capsys):
    root, prepare, sleeps, calls = watch
    prepare(
        [
            {"state": "performed:candidate_verified", "wait": False},
            {"state": "candidate_verified", "wait": False},
            {"state": "in_progress", "wait": False},
            {"state": "retaining", "wait": False},
            {"state": "workflow_complete"},
        ]
    )
    cli.run(root, allow_generation=True, allow_validation=True)
    assert json.loads(capsys.readouterr().out)["state"] == "workflow_complete"
    assert not sleeps and len(calls) == 5
    assert all(row[2] == {"allow_generation": True, "allow_validation": True} for row in calls)


def test_watch_keeps_five_minute_wait_for_pending_cleanup_or_unknown_observation(watch):
    root, prepare, sleeps, calls = watch
    prepare(
        [
            {"state": "recovering:submission_recorded", "wait": True},
            {"state": "retaining", "wait": True},
            {"state": "unknown_observation"},
            {"state": "unknown_observation", "wait": None},
            {"state": "workflow_complete"},
        ]
    )
    cli.run(root)
    assert sleeps == [300, 300, 300, 300] and len(calls) == 5


@pytest.mark.parametrize("state", ["held", "held_unsupported"])
def test_watch_does_not_poll_or_advance_an_admission_or_unsupported_hold(watch, state):
    root, prepare, sleeps, calls = watch
    prepare([{"state": state, "wait": False}])
    with pytest.raises(SystemExit) as result:
        cli.run(root)
    assert result.value.code == 2 and not sleeps and len(calls) == 1


def test_once_remains_one_pass_even_when_ready_or_wait_hint_is_present(watch):
    root, prepare, sleeps, calls = watch
    prepare([{"state": "in_progress", "wait": True}])
    cli.run(root, once=True)
    assert len(calls) == 1 and not sleeps
