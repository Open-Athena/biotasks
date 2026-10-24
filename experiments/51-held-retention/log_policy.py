"""Derive bounded inspection views from verified native control/trial bindings.

Views exist only during public-content inspection. Archives and hashes always
retain original bytes. No grading parser or reward record is changed.
"""

import re
from contextlib import contextmanager

from biotasks.validation import preservation
from biotasks.validation.files import ValidationError, content_sha, require, safe

POLICY = "source-bound-native-verifier-text-v1"
LOGS = ("test-stdout.txt", "test_output.log")


def text_view(raw):
    try:
        raw.decode("utf-8")
    except UnicodeError as error:
        raise ValidationError("Native log is not UTF-8 text with padding") from error
    view = raw.replace(b"\0", b"")
    require(
        all(value >= 32 or value in (9, 10, 13, 27) for value in view),
        "Non-text native control bytes",
    )
    return view


def control_paths(task, control, packed):
    agent = control["agent"]
    name = task["task"] + "-" + agent
    require(
        agent in ("nop", "oracle") and control["name"] == name and control["task"] == task["task"],
        "Native agent/name binding differs",
    )
    trials = control.get("trial_results", [])
    require(len(trials) == 1, "Exactly one source-bound native trial required")
    trial = trials[0]
    result_path = safe(trial["path"])
    pattern = re.escape(name) + "/(" + re.escape(task["task"]) + r"__[A-Za-z0-9_-]+)/result\.json"
    match = re.fullmatch(pattern, result_path)
    require(match is not None, "Native trial path differs")
    trial_name = match.group(1)
    result = trial["result"]
    require(result["trial_name"] == trial_name, "Native trial name differs")
    root = "jobs/" + name + "/" + trial_name + "/"
    return {
        root + "verifier/" + filename
        for filename in LOGS
        if root + "verifier/" + filename in packed
    }, root


def derive(task, controls, packed):
    require(
        len(controls) == 2 and {row["agent"] for row in controls} == {"nop", "oracle"},
        "Native pair identity differs",
    )
    allowed = set()
    roots = []
    for control in controls:
        names, root = control_paths(task, control, packed)
        allowed.update(names)
        roots.append(("jobs/" + control["name"] + "/", root))
    # Other agents, trials and side-loaded files are not covered by this policy.
    for name in packed:
        if not name.startswith("jobs/"):
            continue
        require(
            any(
                name.startswith(trial)
                or name
                in {job + leaf for leaf in ("config.json", "result.json", "job.log", "lock.json")}
                for job, trial in roots
            ),
            "Foreign native job/trial artifact",
        )
    rows = []
    for name, item in packed.items():
        raw = item["data"]
        if b"\0" not in raw:
            continue
        require(name in allowed, "NUL-bearing member is not a bound verifier text log")
        require(
            len(raw) <= 2 * 1024**2 and 0 < raw.count(b"\0") <= 1024**2, "Native inspection bounds"
        )
        view = text_view(raw)
        preservation.inspect(view, name)
        rows.append(
            {
                "path": name,
                "bytes": len(raw),
                "sha256": content_sha(raw),
                "nul_bytes": raw.count(b"\0"),
                "policy": POLICY,
            }
        )
    require(len(rows) <= 4, "Native inspection member bound")
    return sorted(rows, key=lambda row: row["path"])


@contextmanager
def inspection(rows):
    """The caller supplies automatically sealed rows, not operator approvals."""
    require(
        len(rows) <= 4 and len({row["path"] for row in rows}) == len(rows),
        "Native view identity/count",
    )
    expected = {row["path"]: row for row in rows}
    require(
        all(
            re.fullmatch(
                r"jobs/([A-Za-z0-9][A-Za-z0-9_.-]{0,119})-(?:nop|oracle)/\1__[A-Za-z0-9_-]+/verifier/(?:test-stdout\.txt|test_output\.log)",
                name,
            )
            for name in expected
        ),
        "Unknown native inspection path",
    )
    original = preservation.inspect

    def inspect(raw, name, depth=0):
        if b"\0" not in raw or name not in expected:
            return original(raw, name, depth)
        row = expected[name]
        require(
            row["policy"] == POLICY
            and len(raw) == row["bytes"] <= 2 * 1024**2
            and content_sha(raw) == row["sha256"]
            and 0 < raw.count(b"\0") == row["nul_bytes"] <= 1024**2,
            "Sealed inspection bytes changed",
        )
        view = text_view(raw)
        return original(view, name, depth)

    preservation.inspect = inspect
    try:
        yield
    finally:
        preservation.inspect = original
