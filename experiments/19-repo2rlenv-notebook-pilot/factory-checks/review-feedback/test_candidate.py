"""Useful worker feedback must not relax scientific or coverage acceptance."""

import itertools
from types import SimpleNamespace

import pytest
from candidate import PROMPT, PROTOCOL, checker, original_sources, proposed_changes


def review(ids, decision="accept_for_packaging", assessment="unrelated"):
    return SimpleNamespace(
        decision=decision,
        asset_value_assessments=[SimpleNamespace(hint_id=key, decision=assessment) for key in ids],
    )


def outcome(check, record, expected):
    try:
        check(record, [{"hint_id": key} for key in expected])
    except ValueError:
        return False
    return True


def test_candidate_changes_feedback_only_across_coverage_and_scientific_verdicts():
    original = original_sources()[PROTOCOL]
    before, after = checker(original), checker(PROTOCOL.read_text())
    for expected in [[], ["a"], ["a", "b"]]:
        for length in range(4):
            for observed in itertools.product("abc", repeat=length):
                for decision in ["accept_for_packaging", "revise", "blocked"]:
                    for assessment in ["unrelated", "answer_exposure", "unresolved"]:
                        record = review(observed, decision, assessment)
                        assert outcome(before, record, expected) == outcome(after, record, expected)


def test_feedback_identifies_one_wrong_id_in_a_large_otherwise_complete_review():
    check = checker(PROTOCOL.read_text())
    expected = [f"{n:064x}" for n in range(55)]
    typo = "f" * 64
    observed = [*expected[:-1], typo]
    with pytest.raises(ValueError) as error:
        check(review(observed), [{"hint_id": key} for key in expected])
    message = str(error.value)
    assert f"missing_hint_ids={[expected[-1]]}" in message
    assert f"unexpected_hint_ids={[typo]}" in message
    assert "duplicate_hint_ids=[]" in message
    assert "without changing scientific assessments" in message


def test_duplicates_are_reported_even_when_the_expected_set_is_complete():
    check = checker(PROTOCOL.read_text())
    with pytest.raises(ValueError, match=r"duplicate_hint_ids=\['a'\]"):
        check(review(["a", "a"]), [{"hint_id": "a"}])


def test_correct_ids_cannot_clear_an_exposure_or_uncertainty():
    check = checker(PROTOCOL.read_text())
    for assessment in ["answer_exposure", "unresolved"]:
        with pytest.raises(ValueError, match="Acceptance cannot retain"):
            check(review(["a"], assessment=assessment), [{"hint_id": "a"}])


def test_candidate_generation_does_not_modify_canonical_files():
    recorded = {path: path.read_bytes() for path in (PROTOCOL, PROMPT)}
    changes = proposed_changes()
    for path, (before, after) in changes.items():
        assert path.read_bytes() == recorded[path]
        assert before != after
    assert len(changes) == 2


def test_current_protocol_and_prompt_match_the_reviewed_diagnostic_patch():
    for path, (_, after) in proposed_changes().items():
        assert path.read_text() == after
