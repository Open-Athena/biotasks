"""Price complete controller-owned lifetimes, not CPU utilization or model time."""

from datetime import datetime
from decimal import Decimal

RATE = 4 * Decimal("0.0504") + 8 * Decimal("0.0162") + 10 * Decimal("0.000108")


def number(value):
    assert type(value) in (int, float, str)
    result = Decimal(str(value))
    assert result.is_finite()
    return result


def closed_session_bound(session, pipeline, periods, cleanup_seconds):
    assert cleanup_seconds == 300
    assert session["cleanup_verified"] is True
    start, finish = (number(session[key]) for key in ("started", "finished"))
    assert number(pipeline["started"]) <= start < finish <= number(pipeline["finished"])
    assert periods
    intervals = []
    total_reported = Decimal(0)
    for period in periods:
        assert {key: period[key] for key in ("cpu", "ramGB", "diskGB", "gpu")} == {
            "cpu": 4,
            "ramGB": 8,
            "diskGB": 10,
            "gpu": 0,
        }
        left, right = (
            number(datetime.fromisoformat(period[key]).timestamp()) for key in ("startAt", "endAt")
        )
        assert start <= left < right <= finish
        intervals.append((left, right))
        price = number(period["price"])
        assert price >= 0
        total_reported += price
    ordered = sorted(intervals)
    assert all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:], strict=False))
    # The exact admitted runner starts this clock before provider.create, and
    # finishes it after successful owner cleanup. Charge the complete interval,
    # plus the original cleanup allowance at EACH end. Even missing analytics
    # periods cannot reduce this bound. No overlap/idle-state credit is assumed.
    priced_seconds = finish - start + 2 * cleanup_seconds
    bound = priced_seconds * RATE / 3600
    assert total_reported <= bound
    return {
        "session_started": str(start),
        "session_finished_after_cleanup": str(finish),
        "priced_seconds": str(priced_seconds),
        "resource_upper_bound_usd": str(bound),
        "provider_reported_price_usd": str(total_reported),
    }


def admitted_profile(previous):
    """Only the two already audited SDK-only topologies are eligible."""
    base = ("setup-raw", "replay", "materialization-raw", "grading")
    shapes = {
        "sdk_only_four_full_lifetimes_no_serial_assumption": (
            base,
            "3.00",
            "065/reconcile_sdk_only.py",
        ),
        "sdk_only_five_full_lifetimes_one_comparison_repair_no_serial_assumption": (
            (*base, "grading-comparison-repair"),
            "4.00",
            "068/reconcile_sdk_comparison_repair.py",
        ),
    }
    assert previous["applied"] is True and previous["profile"] in shapes
    folders, retained, implementation = shapes[previous["profile"]]
    assert previous["retained_usd"] == retained and previous["priced_sandboxes"] == len(folders)
    return set(folders), Decimal(retained), implementation
