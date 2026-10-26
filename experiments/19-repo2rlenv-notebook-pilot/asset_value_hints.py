"""Advisory final-output matches in hash-verified installed Python source.

This is discovery, not scientific comparison or answer classification. It covers
floating literals in existing priority candidates and numeric CSV/TSV cells only.
Integer-valued constants, comments, strings and other formats remain gaps.
"""

import hashlib
import tokenize
from pathlib import PurePosixPath

import httpx
from asset_literal_inspection import (
    RELATIVE_HINT_DISTANCE,
    csv_matches,
)
from asset_literal_inspection import (
    floating_literals as floating_literals,
)
from package_inspection import normalized


async def build_hints(packages, references, priority, exclusions):
    """Use original installed identities, never a filename match alone."""
    excluded = {(normalized(r["distribution"]), r["path"], r["sha256"]) for r in exclusions}
    selected, candidates, literals = {}, [], []
    for row in priority:
        package = normalized(row["distribution"])
        if (package, row["path"], row["sha256"]) in excluded:
            candidates.append(
                {"distribution": package, "path": row["path"], "status": "declared_excluded"}
            )
        elif PurePosixPath(row["path"]).suffix == ".py":
            selected.setdefault(package, []).append(row)
        else:
            candidates.append(
                {
                    "distribution": package,
                    "path": row["path"],
                    "status": "unsupported_non_python_source",
                }
            )
    for package, assets in selected.items():
        try:
            archive = await packages.archive(package)
        except TimeoutError:
            raise
        except (ValueError, OSError, httpx.HTTPError) as error:
            candidates.extend(
                {
                    "distribution": package,
                    "path": r["path"],
                    "status": "release_source_unavailable",
                    "error_type": type(error).__name__,
                }
                for r in assets
            )
            continue
        with archive:
            members = packages.members(archive)
            for asset in assets:
                packages.remaining()
                record = {
                    "distribution": package,
                    "path": asset["path"],
                    "asset_sha256": asset["sha256"],
                }
                names = [
                    n for n in members if n == asset["path"] or n.endswith("/" + asset["path"])
                ]
                if len(names) != 1:
                    candidates.append({**record, "status": "release_member_unresolved"})
                    continue
                member = members[names[0]]
                digest = hashlib.sha256()
                with packages.open_member(archive, member) as stream:
                    while chunk := stream.read(1024 * 1024):
                        packages.remaining()
                        digest.update(chunk)
                if digest.hexdigest() != asset["sha256"]:
                    candidates.append({**record, "status": "installed_source_identity_differs"})
                    continue
                try:
                    with packages.open_member(archive, member) as stream:
                        observed = list(floating_literals(stream, packages.remaining))
                except (UnicodeError, SyntaxError, tokenize.TokenError):
                    candidates.append({**record, "status": "unreadable_python_tokens"})
                    continue
                literals.extend({**record, **value} for value in observed)
                candidates.append(
                    {
                        **record,
                        "status": "installed_source_literals_inspected",
                        "release_member": names[0],
                        "literal_count": len(observed),
                    }
                )
    findings, coverage = csv_matches(references, literals)
    return {
        "scope": (
            "Advisory magnitude matches between floating Python literals in existing priority "
            "package-source candidates and final hash-verified CSV/TSV cells. Source bytes "
            "must match the recorded installed asset. This is not an exhaustive fixture or "
            "semantic audit. Integer-valued constants, strings, comments, other artifacts "
            "and nonpriority files are not covered. A match may be coincidental or unrelated; "
            "inspect provenance, methods and inputs. Absence is not answer-isolation approval. "
            "The first matching cell is shown and all matching cells are counted."
        ),
        "relative_discovery_distance": RELATIVE_HINT_DISTANCE,
        "distance_is_not_grading_tolerance": True,
        "candidates": candidates,
        "reference_coverage": coverage,
        "findings": findings,
    }
