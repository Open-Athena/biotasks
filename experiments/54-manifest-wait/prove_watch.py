"""Compare actual CLI scheduling on synthetic states, with all transport blocked."""

import argparse
import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from biotasks.generation import cli, planning, resources
from biotasks.validation.files import ValidationError, read_json, require, sha, write_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--proof", type=Path, required=True)
parser.add_argument("--active-plan", type=Path)
args = parser.parse_args()


def audit(event, values):
    if event in {
        "socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
    }:
        raise AssertionError("Scheduling proof must not execute transport")
    if event == "open" and isinstance(values[0], (str, bytes)):
        if any(
            part in str(values[0])
            for part in ("/.codex/secrets/", "/.config/coreweave/", "/.cache/huggingface/token")
        ):
            raise AssertionError("Scheduling proof must not read credentials")


sys.addaudithook(audit)
root = Path(__file__).resolve().parent
scratch = root / "local-scratch"
scratch.mkdir(exist_ok=True)
cases = {
    "ready": [
        {"state": "performed:candidate_verified", "wait": False},
        {"state": "candidate_verified", "wait": False},
        {"state": "in_progress", "wait": False},
        {"state": "retaining", "wait": False},
        {"state": "workflow_complete"},
    ],
    "pending": [
        {"state": "recovering:submission_recorded", "wait": True},
        {"state": "retaining", "wait": True},
        {"state": "unknown_observation"},
        {"state": "workflow_complete"},
    ],
    "held": [{"state": "held", "wait": False}],
    "once": [{"state": "in_progress", "wait": True}],
}
results = {}
original_advance, original_sleep = cli.planning.advance, cli.time.sleep
try:
    with TemporaryDirectory(prefix="watch-", dir=scratch) as temporary:
        work = Path(temporary)
        write_json(
            work / "manifest-plan.json", {"binding": {"manifest": str(work / "synthetic.json")}}
        )
        for name, sequence in cases.items():
            iterator = iter(sequence)
            sleeps, calls = [], []

            def advance(manifest, output, _calls=calls, _iterator=iterator, **flags):
                _calls.append({"manifest": str(manifest), "output": str(output), "flags": flags})
                return next(_iterator)

            cli.planning.advance = advance
            cli.time.sleep = sleeps.append
            stream, exit_code = StringIO(), 0
            with redirect_stdout(stream):
                try:
                    cli.run(work, once=name == "once")
                except SystemExit as error:
                    exit_code = error.code
            results[name] = {
                "passes": len(calls),
                "sleep_seconds": sleeps,
                "total_idle_seconds": sum(sleeps),
                "exit_code": exit_code,
                "result": json.loads(stream.getvalue()),
                "flags_preserved": all(
                    c["flags"] == {"allow_generation": False, "allow_validation": False}
                    for c in calls
                ),
            }
finally:
    cli.planning.advance, cli.time.sleep = original_advance, original_sleep

guard = None
if args.active_plan is not None:
    frozen = read_json(args.active_plan / "manifest-plan.json")
    try:
        planning.verify(Path(frozen["binding"]["manifest"]), args.active_plan)
    except ValidationError as error:
        require(
            str(error) == "Manifest/implementation identity changed",
            "Unexpected active-plan rejection",
        )
        guard = {
            "existing_plan_identity": frozen["plan_identity"],
            "reason": str(error),
            "new_runtime_refused": True,
            "native_model_admission_attempted": False,
        }
    else:
        raise AssertionError("Changed implementation must not adopt the active old plan")

proof = {
    "driver_sha256": sha(Path(__file__)),
    "cli_path": str(Path(cli.__file__).resolve()),
    "cli_sha256": sha(Path(cli.__file__)),
    "generation_code_identity": resources.code_identity(),
    "synthetic_state_sequences": True,
    "real_cli_watch_function": True,
    "transport_and_credentials_forbidden": True,
    "cases": results,
    "changed_active_plan_guard": guard,
    "new_model_calls_or_jobs": 0,
    "native_performance_or_scientific_acceptance_claim": False,
    "temporary_test_state_removed": True,
}
write_json(args.proof, proof)
print(
    json.dumps(
        {
            "proof": str(args.proof),
            "idle_seconds": {name: row["total_idle_seconds"] for name, row in results.items()},
            "active_plan_guard": guard,
        },
        indent=2,
    )
)
