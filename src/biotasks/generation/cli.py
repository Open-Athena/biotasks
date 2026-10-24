"""Installed manifest commands with explicit execution admission."""

import json
import time
import urllib.request
from pathlib import Path

from cyclopts import App

from biotasks.generation import (
    discovery,
    generation_bridge,
    model_budget,
    planning,
    resources,
    source,
)
from biotasks.validation import planning as validation
from biotasks.validation.files import read_json, require, write_json

app = App(name="generate", help="Run bounded official pr_runtime generation and native controls.")


@app.command(name="init-budget")
def init_budget(
    path: Path,
    *,
    cpu_hours: float,
    operating_ceiling_usd: float,
    exclusive_limit_usd: float,
    storage_reserve_usd: float,
) -> None:
    """Create a cumulative ledger. This does not authorize spending/capacity."""
    model_budget.create(
        path.resolve(), cpu_hours, operating_ceiling_usd, exclusive_limit_usd, storage_reserve_usd
    )
    print(str(path.resolve()))


@app.command
def quote(output: Path) -> None:
    """Capture public route prices for the approved model; no model call.

    Existing quotes are validated/reused without a request. Choose a new path
    to capture newer prices. Original runtime still checks prices per request.
    """
    policy = resources.cost_policy()
    if output.exists():
        value = read_json(output)
    else:
        with urllib.request.urlopen(policy.URL, timeout=30) as response:
            raw = response.read(1024**2 + 1)
        require(len(raw) <= 1024**2, "Price quote exceeds bound")
        value = json.loads(raw)
        policy.reservation(value, 2048)
        write_json(output, value)
    print(
        json.dumps(
            {
                "maximum_single_request_reservation_usd": str(policy.reservation(value, 2048)),
                "model_calls": 0,
                "output": str(output.resolve()),
            },
            indent=2,
        )
    )


@app.command
def profile(backend: Path, *, log: Path) -> None:
    """Capture the configured local SDK source identity; no job or model call."""
    value = generation_bridge.call(read_json(backend), {"action": "fingerprint"}, log.resolve())
    print(json.dumps(value, indent=2))


@app.command(name="freeze-candidates")
def freeze_candidates(native_config: Path, *, source_cache: Path, output: Path) -> None:
    """Freeze one bounded official GH listing; no model call or task generation.

    Uses normal gh authentication or an operator-supplied dedicated GH_TOKEN.
    Existing frozen output is verified/reused without another listing.
    """
    result = discovery.freeze(native_config.resolve(), source_cache.resolve(), output.resolve())
    print(
        json.dumps(
            {
                "repo": result["repo"],
                "candidates": len(result["candidates"]),
                "output": str(output.resolve()),
                "model_calls": 0,
            },
            indent=2,
        )
    )


@app.command(name="prepare-source")
def prepare_source(
    work_dir: Path, *, archive: Path | None = None, dependency: Path | None = None
) -> None:
    """Acquire pinned official source and local-export writer; execute neither.

    Optional archive/dependency files must match the bundled original hashes.
    Existing caches are verified without downloads. Interrupted staging is held.
    """
    work_dir = work_dir.resolve()
    receipt = source.acquire(work_dir, archive=archive, dependency=dependency)
    print(
        json.dumps(
            {
                "receipt_identity": receipt["receipt_identity"],
                "source": source.configuration(work_dir),
            },
            indent=2,
        )
    )


@app.command
def identities() -> None:
    """Report installed source identities, without transport or credential access."""
    print(
        json.dumps(
            {
                "generation_code_identity": resources.code_identity(),
                "validation_code_identity": validation.code_identity(),
                "repo2rlenv_revision": validation.UPSTREAM,
            },
            indent=2,
        )
    )


@app.command
def plan(manifest: Path, *, work_dir: Path) -> None:
    """Freeze declared inputs offline; no discovery, model call or job admission."""
    result = planning.prepare(manifest.resolve(), work_dir.resolve())
    print(
        json.dumps(
            {
                "plan_identity": result["plan_identity"],
                "cases": result["cases"],
                "model_calls": 0,
                "remote_jobs": 0,
            },
            indent=2,
        )
    )


@app.command
def status(work_dir: Path) -> None:
    """Verify local source bindings and journals without remote queries."""
    work_dir = work_dir.resolve()
    frozen = read_json(work_dir / "manifest-plan.json")
    _, verified = planning.verify(Path(frozen["binding"]["manifest"]), work_dir)
    print(
        json.dumps(
            {
                "plan_identity": verified["plan_identity"],
                "cases": verified["cases"],
                "execution": {
                    case["id"]: {
                        name: read_json(work_dir / case["id"] / "runs/generation" / name)
                        for name in ("journal.json", "held.json")
                        if (work_dir / case["id"] / "runs/generation" / name).exists()
                    }
                    for case in verified["cases"]
                },
            },
            indent=2,
        )
    )


@app.command
def run(
    work_dir: Path,
    *,
    once: bool = False,
    allow_generation: bool = False,
    allow_validation: bool = False,
) -> None:
    """Advance serial cases through existing admitted lifecycles.

    Execution flags retain ledger gates and do not authorize spending. Default
    watch interval is five minutes; --once returns after one pass for a scheduler.
    No stage retries a model request or chooses a replacement PR.
    """
    work_dir = work_dir.resolve()
    frozen = read_json(work_dir / "manifest-plan.json")
    manifest = Path(frozen["binding"]["manifest"])
    while True:
        result = planning.advance(
            manifest, work_dir, allow_generation=allow_generation, allow_validation=allow_validation
        )
        state = result["state"]
        if state.startswith("held"):
            print(json.dumps(result, indent=2))
            raise SystemExit(2)
        if once or state in {
            "workflow_complete",
            "local_export_prepared",
            "generation_not_admitted",
        }:
            print(json.dumps(result, indent=2))
            return
        time.sleep(300)
