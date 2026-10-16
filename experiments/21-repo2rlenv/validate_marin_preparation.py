"""Validate prepared JSON with the exact Marin checkout on a remote CPU worker."""

import json
import os
import subprocess
from pathlib import Path

REVISION = "45a044387ccd95ab698b4a592056aadaff961540"


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Remote worker required")
    repo = Path("/work/marin")
    repo.mkdir()
    evidence = Path("/evidence/native")
    with (evidence / "marin-setup.log").open("w") as log:
        for command in (
            ["apt-get", "update"],
            [
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                "build-essential",
                "python3-dev",
            ],
            ["git", "init", str(repo)],
            [
                "git",
                "-C",
                str(repo),
                "remote",
                "add",
                "origin",
                "https://github.com/marin-community/marin.git",
            ],
            ["git", "-C", str(repo), "fetch", "--depth=1", "origin", REVISION],
            ["git", "-C", str(repo), "checkout", "--detach", "FETCH_HEAD"],
            [
                "uv",
                "sync",
                "--frozen",
                "--no-dev",
                "--package",
                "marin-taskcompendium",
                "--python",
                "3.12.3",
                "--project",
                str(repo),
            ],
        ):
            subprocess.run(command, stdout=log, stderr=log, timeout=1800, check=True)
    actual = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != REVISION:
        raise ValueError("Unexpected Marin revision")
    check = """
import json
from pathlib import Path
from taskcompendium.models import TaskSpec, require_resolved_environment
from shellbox.machine import UnsupportedMachineSpec
p=Path('/work/native/task.json')
t=TaskSpec.model_validate_json(p.read_text())
Path('/evidence/native/validated-task.json').write_text(t.model_dump_json(indent=2)+'\\n')
assert not t.resources.worker and not t.resources.all
assert t.resources.oracle and t.resources.verifier
try:
    require_resolved_environment(t.environment_requirements)
except UnsupportedMachineSpec:
    rejected=True
else:
    raise AssertionError('An unresolved build must not be executable')
Path('/evidence/native/schema-result.json').write_text(json.dumps({
 'status':'schema_validated_only', 'task_id':t.id,
 'marin_revision':'45a044387ccd95ab698b4a592056aadaff961540',
 'unresolved_execution_rejected':rejected,
 'worker_resources':len(t.resources.worker),
 'oracle_resources':len(t.resources.oracle),
 'verifier_resources':len(t.resources.verifier),
 'native_reward_preserved_in_spec':True,
 'runtime_parity_executed':False,
 'isolation_executed':False
},indent=2)+'\\n')
"""
    with (evidence / "schema-check.log").open("w") as log:
        result = subprocess.run(
            [str(repo / ".venv/bin/python"), "-c", check], stdout=log, stderr=log, timeout=120
        )
    (evidence / "process-result.json").write_text(
        json.dumps({"marin_revision": actual, "returncode": result.returncode}) + "\n"
    )
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
