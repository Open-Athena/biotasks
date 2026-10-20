"""Real small subprocess checks for controller-owned command output."""

import json
import sys
from pathlib import Path

import pytest
import reference_remote


@pytest.mark.parametrize("timeout", [False, True])
def test_worker_cleanup_cannot_remove_active_command_log(tmp_path, monkeypatch, capsys, timeout):
    logs = tmp_path / "logs"

    def routed_path(*parts):
        if parts[0] == "/work/logs":
            return logs.joinpath(*parts[1:])
        return Path(*parts)

    monkeypatch.setattr(reference_remote, "Path", routed_path)
    code = (
        "import shutil,sys,time\n"
        "print('before cleanup',flush=True)\n"
        f"shutil.rmtree({str(logs)!r})\n"
        "print('after cleanup',file=sys.stderr,flush=True)\n"
        + ("time.sleep(5)\n" if timeout else "sys.exit(7)\n")
    )
    reference_remote.execute(
        [sys.executable, "-c", code], 0.5 if timeout else 5, str(tmp_path), "trial"
    )
    record = json.loads(capsys.readouterr().out)
    assert record["timed_out"] is timeout
    assert record["exit_code"] != 0 if timeout else record["exit_code"] == 7
    assert (logs / "trial.log").read_text() == "before cleanup\nafter cleanup\n"
    assert json.loads((logs / "trial.json").read_text()) == record
    assert sorted(p.name for p in logs.iterdir()) == ["trial.json", "trial.log"]
