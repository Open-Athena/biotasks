"""Bound already-cleaned serial resources by their enclosing observed clock.

This does not price CPU utilization or discount model thinking/idle time. It
charges two full resource profiles throughout the entire campaign interval,
including 300 seconds before and after it. Callers must retain the original
seven-owner, native-backend, source and cleanup checks.
"""

import math
import sys
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "070"))
from closed_session_bound import admitted_implementation  # noqa: E402

SDK_STAGES = ("setup", "replay", "construction", "grading")


def finite(value):
    assert type(value) in (int, float) and math.isfinite(value)
    return Decimal(str(value))


def observed_bound(pipeline, sessions, native_intervals, sources, rate):
    admitted_implementation(sources)
    assert pipeline["status"] == "validated"
    assert set(sessions) == set(SDK_STAGES)
    begin, end = (finite(pipeline[k]) for k in ("started", "finished"))
    assert 0 < end - begin <= 7200
    stages = {row["name"]: row for row in pipeline["stages"]}
    assert all(row["status"] == "completed" for row in stages.values())
    assert [row["name"] for row in pipeline["stages"]] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
        "native",
    ]
    assert all(
        finite(a["finished"]) <= finite(b["started"])
        for a, b in zip(pipeline["stages"], pipeline["stages"][1:], strict=False)
    )
    assert begin <= finite(pipeline["stages"][0]["started"])
    assert finite(pipeline["stages"][-1]["finished"]) <= end
    for name, session in sessions.items():
        assert session["cleanup_verified"] is True
        left, right = (finite(session[k]) for k in ("started", "finished"))
        assert (
            begin
            <= finite(stages[name]["started"])
            <= left
            < right
            <= finite(stages[name]["finished"])
            <= end
        )
    assert len(native_intervals) == 3
    for left, right in native_intervals:
        assert (
            finite(stages["native"]["started"])
            <= finite(left)
            < finite(right)
            <= finite(stages["native"]["finished"])
        )
    assert all(
        finite(a[1]) <= finite(b[0])
        for a, b in zip(native_intervals, native_intervals[1:], strict=False)
    )
    # One known SDK sandbox per stage and one native trial at a time, with
    # verified deletion before each wrapper finishes. Preserve the preceding
    # auditor's TWO-profile bound, now over a proved enclosing clock rather
    # than assuming every completed campaign used its full 7200 seconds.
    seconds = end - begin + 600
    assert rate.is_finite() and rate == Decimal("0.332280")
    upper = 2 * rate * seconds / 3600
    keep = ((upper + Decimal("0.10")) / Decimal("0.25")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("0.25")
    assert upper < keep < Decimal(2)
    return {
        "observed_pipeline_seconds": str(end - begin),
        "seconds_each_including_both_300_second_margins": str(seconds),
        "full_resource_profiles": 2,
        "resource_upper_bound_usd": str(upper),
        "retained_usd": f"{keep:.2f}",
        "additional_margin_usd": str(keep - upper),
    }
