"""Three synthetic input rebuilds; no model, dependencies or scientific run."""

import argparse
import asyncio
import gzip
import importlib.util
import json
from pathlib import Path

from reference_setup import SetupSession

BASE = Path(__file__).resolve().parents[1] / "daytona-session-transport/run_live_check.py"
spec = importlib.util.spec_from_file_location("staging_check_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


async def checks(remote, root):
    results = []
    for name in ("stable", "volatile-metadata", "changed-data"):
        case = root / "cases" / name
        case.mkdir(parents=True)
        initialized = await remote.command(
            ["mkdir", "-p", "/work/setup", "/inputs", "/work/cache"], 20, name + "-initialize"
        )
        assert initialized["exit_code"] == 0
        sentinel = case / "sentinel.txt"
        sentinel.write_text("synthetic authoring workspace\n")
        await remote.upload(sentinel, "/work/setup/sentinel.txt")
        source = (
            "import gzip\nfrom pathlib import Path\n"
            f"counter=Path('/work/probe-counts/{name}.txt')\n"
            "n=int(counter.read_text())+1 if counter.exists() else 1\n"
            "counter.write_text(str(n))\n"
            "payload=b'synthetic input only\\n'\n"
            + (
                "payload=b'changed input only\\n' if n>1 else payload\n"
                if name == "changed-data"
                else ""
            )
            + "data=gzip.compress(payload,mtime="
            + ("n" if name == "volatile-metadata" else "0")
            + ")\nPath('/inputs/data.gz').write_bytes(data)\n"
        )
        staging = case / "stage-inputs.sh"
        staging.write_text("#!/bin/sh\nset -eu\npython - <<'PY'\n" + source + "PY\n")
        await remote.upload(staging, "/work/stage-inputs.sh")
        built = await remote.command(
            ["sh", "-eu", "/work/stage-inputs.sh"], 20, name + "-first-build"
        )
        assert built["exit_code"] == 0
        declaration = case / "declared-inputs.json"
        base.save_record(
            declaration,
            {"files": [{"local_path": "/inputs/data.gz", "source": "synthetic control"}]},
        )
        await remote.upload(declaration, "/work/declared-inputs.json")
        first = await remote.helper(
            ["snapshot-inputs", "/work/declared-inputs.json", "/work/control-inputs.json"],
            name + "-first-snapshot",
        )
        base.save_record(case / "inputs-before.json", first)
        before = case / "before.gz"
        await remote.download("/inputs/data.gz", before)
        worker = SetupSession(
            prepared=None,
            remote=remote,
            root=case / "session",
            setup_seconds=90,
            reference_seconds=10,
            max_tests=1,
        )
        expected_failure = name != "stable"
        try:
            comparison = await worker.check_staging_reproducibility(case, first)
        except ValueError as error:
            assert expected_failure and "not byte-reproducible" in str(error)
            comparison = json.loads((case / "staging-recheck/comparison.json").read_text())
            base.save_record(
                case / "feedback.json", {"error": str(error), "scientific_dispatches": 0}
            )
        else:
            assert not expected_failure and comparison["status"] == "byte_identical"
        after = case / "after.gz"
        await remote.download("/inputs/data.gz", after)
        assert (gzip.decompress(before.read_bytes()) == gzip.decompress(after.read_bytes())) == (
            name != "changed-data"
        )
        assert (before.read_bytes() == after.read_bytes()) == (name == "stable")
        restored = case / "sentinel-restored.txt"
        await remote.download("/work/setup/sentinel.txt", restored)
        assert restored.read_bytes() == sentinel.read_bytes()
        # The original replay check still refuses changed bytes; no receipt is
        # rewritten or compression metadata normalized by the controller.
        await remote.upload(case / "inputs-before.json", "/work/expected-control-inputs.json")
        try:
            await remote.helper(
                ["verify-staging", "/work/expected-control-inputs.json"],
                name + "-strict-original-check",
            )
        except RuntimeError:
            assert expected_failure
            operation = root / "operations" / f"{remote.operation:04d}"
            assert "Staged file checksum mismatch" in (operation / "output.log").read_text()
        else:
            assert not expected_failure
        assert worker.tests == 0 and not remote.uncertain
        results.append(
            {
                "name": name,
                "passed": True,
                "rebuild_status": comparison["status"],
                "same_decoded_payload": name != "changed-data",
                "exact_bytes_equal": name == "stable",
                "scientific_dispatches": 0,
                "authoring_workspace_restored": True,
                "strict_original_hash_gate_preserved": True,
                "setup_seconds_remaining": worker.setup_remaining,
            }
        )
    return results


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
