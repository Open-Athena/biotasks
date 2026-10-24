"""Prototype import-origin report; execute only inside the intended sandbox.

This imports requested modules. Local use is restricted to our synthetic fixture;
untrusted biology code must be inspected in its own target environment, never in
the trusted controller. This reports origin, not reward or verified Git parity.
"""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import sys
from pathlib import Path


def collect(checkout, project, modules):
    root = Path(checkout).resolve(strict=True)
    rows = []
    try:
        distribution = importlib.metadata.distribution(project)
        direct = distribution.read_text("direct_url.json")
        metadata = {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
            "direct_url": json.loads(direct) if direct else None,
        }
    except (importlib.metadata.PackageNotFoundError, ValueError) as error:
        metadata = {"error": type(error).__name__}
    previous_bytecode_policy = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        rows = imported_rows(root, modules)
    finally:
        sys.dont_write_bytecode = previous_bytecode_policy
    states = {row["state"] for row in rows}
    state = (
        "ambiguous"
        if not rows or "ambiguous" in states
        else "foreign"
        if "foreign" in states
        else "checkout"
    )
    return {
        "schema_version": 1,
        "checkout": str(root),
        "project": project,
        "distribution": metadata,
        "modules": rows,
        "binding": state,
        "git_revision_or_reward_verified": False,
        "installation_or_sys_path_changed_by_collector": False,
    }


def imported_rows(root, modules):
    rows = []
    for name in modules:
        row = {"module": name}
        try:
            module = importlib.import_module(name)
            path = getattr(module, "__file__", None)
            row["declared_file"] = path
            if path is None:
                row.update(state="ambiguous", reason="Module has no single source file")
            else:
                resolved = Path(path).resolve(strict=True)
                if resolved.suffix != ".py" or resolved.stat().st_size > 2 * 1024**2:
                    row.update(
                        state="ambiguous", reason="Not a bounded ordinary Python source module"
                    )
                    rows.append(row)
                    continue
                row.update(
                    realpath=str(resolved),
                    state="checkout" if resolved.is_relative_to(root) else "foreign",
                    source_file_sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
                )
        except Exception as error:
            row.update(state="ambiguous", error=type(error).__name__)
        rows.append(row)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--module", action="append", required=True)
    args = parser.parse_args()
    print(json.dumps(collect(args.checkout, args.project, args.module), indent=2))
