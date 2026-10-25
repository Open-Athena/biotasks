"""Price complete controller-owned lifetimes, not CPU utilization or model time."""

from datetime import datetime
from decimal import Decimal

RATE = 4 * Decimal("0.0504") + 8 * Decimal("0.0162") + 10 * Decimal("0.000108")


def terminal_state(pipeline):
    """Match a final grading outcome to its required typed host state."""
    stages = pipeline["stages"]
    assert [s["name"] for s in stages] == [
        "preparation",
        "setup",
        "replay",
        "specification",
        "construction",
        "grading",
    ]
    assert all(s["status"] == "completed" for s in stages[:-1])
    if pipeline["status"] == "rejected":
        assert stages[-1]["status"] == "rejected"
        return "SUCCEEDED"
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline.get("failed_stage") == "grading" and stages[-1]["status"] == "incomplete"
    return "FAILED"


def admitted_implementation(sources):
    """Exact creator/session pairs with identical creation and cleanup logic.

    The later creator only adds static source-operation context to the worker.
    The newest pair only adds fail-closed network-result checks and catches a
    typed export-repair rejection. None changes resource creation or cleanup.
    The earlier exact triple predates the full-budget guard refactor and one
    source-path argument to dependency inspection; its creator is byte-identical.
    Every pair must also have passed its preceding lifetime auditor.
    """
    assert set(sources) == {"run_autonomous.py", "run_reference_setup.py", "reference_setup.py"}
    if sources == {
        "run_autonomous.py": "d90fd8c6f121d46c0f6bc6faea54172f18035887ba07dca076609f2e6d16bae9",
        "run_reference_setup.py": "34ae1de16e432cb6926e9d0f56158a35d65bebe3b06b5c4769f86d53c145eb2a",
        "reference_setup.py": "a73ff8ccfbc5281a51ba55817316f33d8d3398d4227c4218f6bf0e553c3b2c83",
    }:
        return dict(sources)
    if sources == {
        "run_autonomous.py": "972b6315182a86988dab558ec42e63891d2dd8a380ae224253d209f476db3b12",
        "run_reference_setup.py": "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
        "reference_setup.py": "a73ff8ccfbc5281a51ba55817316f33d8d3398d4227c4218f6bf0e553c3b2c83",
    }:
        return dict(sources)
    assert sources["run_autonomous.py"] == (
        "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188"
    )
    assert (sources["run_reference_setup.py"], sources["reference_setup.py"]) in {
        (
            "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
            "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
        ),
        (
            "fc83bf2ecd9f201b4bfd8c47cb07740619d09c66fc8df5a37435eb95af5b2d0b",
            "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
        ),
        (
            "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8",
            "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7",
        ),
    }
    return dict(sources)


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
    # Analytics is an optional independent cross-check, never the accounting
    # clock. Even no returned usage periods cannot shorten a closed lifetime.
    assert isinstance(periods, list)
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
        "provider_reported_price_usd": str(total_reported) if periods else None,
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
