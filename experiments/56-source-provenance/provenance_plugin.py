"""Explicit opt-in pytest observation candidate; no grading or import repair."""

import json
from pathlib import Path

from process_snapshot import snapshot


def pytest_addoption(parser):
    group = parser.getgroup("biotasks-provenance")
    group.addoption("--bt-origin-root", required=True)
    group.addoption("--bt-origin-project", required=True)
    group.addoption("--bt-origin-module", action="append", default=[])
    group.addoption("--bt-origin-report", required=True)


def observe(config, phase):
    try:
        value = snapshot(
            config.getoption("--bt-origin-root"),
            config.getoption("--bt-origin-project"),
            config.getoption("--bt-origin-module"),
            phase,
        )
    except Exception as error:
        value = {"phase": phase, "observation_error": type(error).__name__}
    config._bt_origin_events.append(value)


def pytest_configure(config):
    config._bt_origin_events = []


def pytest_collection_finish(session):
    observe(session.config, "collection_finish")


def pytest_sessionfinish(session, exitstatus):
    observe(session.config, "session_finish")
    output = {
        "schema_version": 1,
        "pytest_exitstatus": int(exitstatus),
        "events": session.config._bt_origin_events,
        "reporting_only": True,
        "scientific_acceptance": False,
        "limit": "Only named loaded modules and observed top-level functions/methods; not complete executing-code identity",
    }
    # A failed write is explicit in pytest diagnostics; it is never a valid receipt.
    Path(session.config.getoption("--bt-origin-report")).write_text(
        json.dumps(output, indent=2) + "\n"
    )
