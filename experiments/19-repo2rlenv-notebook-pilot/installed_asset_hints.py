"""Read advisory numeric hints from the actual task environment, without imports.

Run with the task interpreter for distribution ownership. Scientific packages are
never imported or executed. This neither selects removals nor certifies isolation.
"""

import hashlib
import importlib.metadata
import json
import re
import sys
import sysconfig
import tempfile
import time
import tokenize
from pathlib import Path, PurePosixPath

from asset_literal_inspection import RELATIVE_HINT_DISTANCE, csv_matches, floating_literals


def normalized(value):
    return re.sub(r"[-_.]+", "-", value).casefold()


class References:
    def __init__(self, root, files, deadline):
        self.root, self.deadline, self.catalog = Path(root), deadline, {}
        for row in files:
            name = row["path"]
            relative = PurePosixPath(name)
            if (
                not name
                or relative.is_absolute()
                or relative.as_posix() != name
                or ".." in relative.parts
                or name in self.catalog
                or type(row["bytes"]) is not int
                or row["bytes"] < 0
                or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
            ):
                raise ValueError("Invalid final reference identity")
            self.catalog[name] = {key: row[key] for key in ("sha256", "bytes")}

    def remaining(self):
        if time.time() >= self.deadline:
            raise TimeoutError("Existing construction deadline exhausted")


def installed_path(asset, distribution, roots):
    name = asset["path"]
    relative = PurePosixPath(name)
    if relative.is_absolute() or relative.as_posix() != name or ".." in relative.parts:
        raise ValueError("Invalid distribution-relative candidate")
    owner = distribution(asset["distribution"])
    if normalized(owner.metadata["Name"]) != normalized(asset["distribution"]):
        raise ValueError("Candidate distribution identity differs")
    if name not in {str(path) for path in owner.files or []}:
        raise ValueError("Candidate not owned by installed distribution")
    path = Path(owner.locate_file(name))
    root = next((root for root in roots if path.is_relative_to(root)), None)
    if root is None or path.resolve() != path or not path.is_file():
        raise ValueError("Candidate is not an installed regular file")
    if any(p.is_symlink() for p in [path, *path.parents] if p != root):
        raise ValueError("Linked candidate is not installed evidence")
    return path


def build_hints(
    catalog,
    reference_root,
    reference_files,
    exclusions,
    deadline,
    *,
    scratch,
    distribution=importlib.metadata.distribution,
    roots=None,
):
    """Hash-bound snapshots keep tokenization tied to the installed observation."""
    references = References(reference_root, reference_files, deadline)
    roots = roots or [Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")]
    excluded = {(normalized(r["distribution"]), r["path"], r["sha256"]) for r in exclusions}
    candidates, literals, seen = [], [], set()
    for asset in catalog["summary"]["priority_matches"]:
        references.remaining()
        if asset not in catalog["files"]:
            raise ValueError("Priority candidate differs from final installed catalog")
        key = normalized(asset["distribution"]), asset["path"]
        if key in seen:
            raise ValueError("Duplicate installed candidate identity")
        seen.add(key)
        record = {"distribution": key[0], "path": asset["path"], "asset_sha256": asset["sha256"]}
        if (*key, asset["sha256"]) in excluded:
            candidates.append({**record, "status": "declared_excluded"})
            continue
        if PurePosixPath(asset["path"]).suffix != ".py":
            candidates.append({**record, "status": "unsupported_non_python_source"})
            continue
        try:
            path = installed_path(asset, distribution, roots)
            # The unnamed file lives under root-owned private storage and is
            # removed on every exit, including deadline and tokenizer failure.
            with tempfile.TemporaryFile(dir=scratch) as snapshot:
                digest, size = hashlib.sha256(), 0
                with path.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        references.remaining()
                        digest.update(chunk)
                        size += len(chunk)
                        snapshot.write(chunk)
                if digest.hexdigest() != asset["sha256"] or size != asset["bytes"]:
                    candidates.append({**record, "status": "installed_asset_identity_differs"})
                    continue
                snapshot.seek(0)
                observed = list(floating_literals(snapshot, references.remaining))
        except TimeoutError:
            raise
        except (ValueError, OSError, importlib.metadata.PackageNotFoundError) as error:
            candidates.append(
                {
                    **record,
                    "status": "installed_asset_unavailable",
                    "error_type": type(error).__name__,
                }
            )
            continue
        except (UnicodeError, SyntaxError, tokenize.TokenError):
            candidates.append({**record, "status": "unreadable_python_tokens"})
            continue
        literals.extend({**record, **value} for value in observed)
        candidates.append(
            {
                **record,
                "status": "installed_source_literals_inspected",
                "literal_count": len(observed),
            }
        )
    findings, coverage = csv_matches(references, literals)
    references.remaining()
    return {
        "scope": "Advisory magnitude matches in hash/size-verified Python files owned by the actual installed distribution and final CSV/TSV references. No package imports, scientific execution, network requests, removal or isolation verdict. Integer-valued constants, comments, strings, nonpriority files and other formats are gaps. Matches can be unrelated; absence is not approval.",
        "relative_discovery_distance": RELATIVE_HINT_DISTANCE,
        "distance_is_not_grading_tolerance": True,
        "candidates": candidates,
        "reference_coverage": coverage,
        "findings": findings,
    }


def main():
    catalog, files, root, exclusions, deadline, output = sys.argv[1:]
    catalog_raw, files_raw = Path(catalog).read_bytes(), Path(files).read_bytes()
    result = build_hints(
        json.loads(catalog_raw),
        root,
        json.loads(files_raw),
        json.loads(Path(exclusions).read_text())["files"],
        float(deadline),
        scratch=Path(output).parent,
    )
    result["source"] = {
        "asset_catalog_sha256": hashlib.sha256(catalog_raw).hexdigest(),
        "reference_inventory_sha256": hashlib.sha256(files_raw).hexdigest(),
    }
    Path(output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
