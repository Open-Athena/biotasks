"""Exercise controller workspace operations with synthetic files, never biology."""

import argparse
import asyncio
import importlib.util
import json
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "daytona-session-transport/run_live_check.py"
spec = importlib.util.spec_from_file_location("workspace_compatibility_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


async def checks(remote, root):
    await remote.network(False)
    await remote.network(True)
    fixture = root / "synthetic-input.txt"
    fixture.write_text("synthetic original\n")
    created = await remote.command(
        ["mkdir", "-p", "/work/setup", "/inputs"], 30, "fixture-directories"
    )
    assert created["exit_code"] == 0 and not created["timed_out"]
    await remote.upload(fixture, "/work/setup/scratch.txt")
    token = uuid.uuid4().hex
    assert await remote.helper(["isolate-authoring-workspace", token], "isolate-first") == {
        "state": "isolated",
        "workspace": "/work/setup",
    }
    missing = await remote.command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "assert not Path('/work/setup').exists()\n"
            "Path('/inputs/copied.txt').write_bytes(Path('/work/setup/scratch.txt').read_bytes())\n",
        ],
        30,
        "scratch-copy-must-fail",
    )
    assert missing["exit_code"] == 1 and not missing["timed_out"]
    assert "FileNotFoundError" in missing["log"] and "/work/setup/scratch.txt" in missing["log"]
    independent = await remote.command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "assert not Path('/work/setup').exists()\n"
            "Path('/inputs/independent.txt').write_text('synthetic staged\\n')\n",
        ],
        30,
        "independent-staging",
    )
    assert independent["exit_code"] == 0 and not independent["timed_out"]
    restored = await remote.helper(["restore-authoring-workspace", token], "restore-first")
    assert restored["state"] == "restored" and restored["authoring_path_recreated"] is False
    verified = await remote.command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "assert Path('/work/setup/scratch.txt').read_text() == 'synthetic original\\n'\n"
            "assert Path('/inputs/independent.txt').read_text() == 'synthetic staged\\n'\n",
        ],
        30,
        "verify-first-restoration",
    )
    assert verified["exit_code"] == 0 and not verified["timed_out"]
    cases = [
        {
            "name": "workspace_absent_then_original_restored",
            "passed": True,
            "network_policy_controls_verified": True,
            "scratch_copy_failed_before_science": True,
            "original_bytes_restored": True,
            "synthetic_inputs": True,
        },
        {
            "name": "self_contained_staging_while_workspace_absent",
            "passed": True,
            "staged_bytes_verified": True,
            "synthetic_inputs": True,
        },
    ]
    token = uuid.uuid4().hex
    await remote.helper(["isolate-authoring-workspace", token], "isolate-second")
    recreated = await remote.command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "Path('/work/setup').mkdir()\n"
            "Path('/work/setup/scratch.txt').write_text('unexpected staging edit\\n')\n",
        ],
        30,
        "recreate-reserved-workspace",
    )
    assert recreated["exit_code"] == 0 and not recreated["timed_out"]
    restored = await remote.helper(["restore-authoring-workspace", token], "restore-second")
    assert restored["state"] == "restored" and restored["authoring_path_recreated"] is True
    preserved = restored["preserved_staging_path"]
    verified = await remote.command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "assert Path('/work/setup/scratch.txt').read_text() == 'synthetic original\\n'\n"
            f"assert Path({preserved!r}, 'scratch.txt').read_text() == 'unexpected staging edit\\n'\n",
        ],
        30,
        "verify-preserved-unexpected-state",
    )
    assert verified["exit_code"] == 0 and not verified["timed_out"]
    cases.append(
        {
            "name": "unexpected_workspace_preserved_and_original_restored",
            "passed": True,
            "recreation_reported": True,
            "both_byte_versions_retained": True,
            "synthetic_inputs": True,
        }
    )
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
        )
    )
