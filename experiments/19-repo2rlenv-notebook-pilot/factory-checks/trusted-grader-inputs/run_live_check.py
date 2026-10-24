"""Reuse the bounded transport check's creation and exact-owner cleanup lifecycle."""

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent / "daytona-session-transport/run_live_check.py"
SPEC = importlib.util.spec_from_file_location("bounded_daytona_check", TRANSPORT)
TRANSPORT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSPORT_MODULE)


async def checks(remote, root):
    from scientific_bundle import VERIFY

    for source, destination in (
        (HERE.parents[1] / "grading_remote.py", "/work/grading_remote.py"),
        (HERE / "sandbox_check.py", "/work/sandbox_check.py"),
    ):
        await remote.upload(source, destination)
    template = root / "verify-template.py"
    template.write_text(VERIFY)
    await remote.upload(template, "/work/verify-template.py")
    result = await remote.command(["python", "/work/sandbox_check.py"], 60, "trusted-inputs")
    if result["exit_code"] != 0 or result["timed_out"]:
        raise ValueError("Synthetic input-boundary command failed: " + result["log"])
    observed = json.loads(result["log"])
    if observed["model_calls"] != 0 or observed["scientific_computation"]:
        raise ValueError("Unexpected model or scientific execution")
    return observed["cases"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    sources = [
        TRANSPORT,
        HERE / "sandbox_check.py",
        Path(__file__),
        HERE.parents[1] / "grading_remote.py",
        HERE.parents[1] / "scientific_bundle.py",
    ]
    assert config["source_sha256"] == {
        str(p.relative_to(HERE.parents[3])): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sources
    }
    result = asyncio.run(TRANSPORT_MODULE.run(config, args.root, checks=checks))
    print(json.dumps(result))
