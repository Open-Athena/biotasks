"""Apply worker-declared unused answer-file exclusions inside the task environment.

The worker establishes answer relevance and unused status; this helper checks
exact installed ownership/content and records deletion. It never selects files.
"""

import ast
import csv
import hashlib
import importlib.metadata
import json
import re
import sys
import sysconfig
from pathlib import Path, PurePosixPath


def imported_module_terms(source):
    """Literal import names are discovery hints, never execution evidence."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.rsplit(".", 1)[-1].casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.rsplit(".", 1)[-1].casefold())
            names.update(alias.name.casefold() for alias in node.names if alias.name != "*")
    return sorted(names)


def imported_member_groups(source):
    """Collect literal from-imports without executing or resolving the modules."""
    groups = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            module = "." * node.level + node.module
            groups.setdefault(module, set()).update(
                alias.name for alias in node.names if alias.name != "*"
            )
    return groups


def shared_import_groups(source_groups, candidate_source):
    """Surface shared input-name groups, including differently named test modules.

    A common module leaf and at least two literal members are only a discovery
    relationship. Namespace shims, dormant imports and matching names do not
    establish identical inputs, execution, an answer, or safe removal.
    """
    matches = []
    for candidate_module, members in imported_member_groups(candidate_source).items():
        for source_module, source_members in source_groups.items():
            shared = sorted(members & source_members)
            if (
                candidate_module.rsplit(".", 1)[-1] == source_module.rsplit(".", 1)[-1]
                and len(shared) >= 2
            ):
                matches.append(
                    {
                        "source_module": source_module,
                        "candidate_module": candidate_module,
                        "members": shared,
                    }
                )
    return sorted(matches, key=lambda row: (row["source_module"], row["candidate_module"]))


def inspect_assets(
    outputs, *, distributions=importlib.metadata.distributions, roots=None, source=None
):
    """Expose actual installed answer candidates; do not judge or remove them.

    Names/formats and test/example locations are discovery hints. A differing
    hash does not establish that a fixture lacks the requested scientific answer.
    """
    roots = roots or [Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")]
    source_terms = imported_module_terms(source) if source is not None else []
    source_groups = imported_member_groups(source) if source is not None else {}
    source_patterns = [
        (term, re.compile(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"))
        for term in source_terms
    ]
    candidates, inspected, coverage = [], 0, []
    for installed in distributions():
        distribution = installed.metadata["Name"]
        normalized = re.sub(r"[-_.]+", "-", distribution).casefold()
        # A dedicated test distribution often stores fixtures directly under
        # its package/data directory, with no separate "tests" path segment.
        # This is a discovery hint, never evidence of an answer or unused file.
        dedicated_tests = normalized.endswith(("tests", "testsuite", "test-suite"))
        package_inspected, package_candidates = 0, 0
        for relative in installed.files or []:
            name = str(relative)
            path = Path(installed.locate_file(relative))
            if not any(path.is_relative_to(root) for root in roots):
                continue
            if path.is_symlink() or path.resolve() != path or not path.is_file():
                continue
            inspected += 1
            package_inspected += 1
            parts = PurePosixPath(name).parts[:-1]
            if (
                parts
                and re.sub(r"[-_.]+", "-", parts[0]).casefold()
                == re.sub(r"[-_.]+", "-", distribution).casefold()
            ):
                parts = parts[1:]  # A package named "example" is not an examples directory.
            packaged_test = dedicated_tests or any(
                part.lower() in {"test", "tests", "example", "examples"} for part in parts
            )
            matches = []
            for output in outputs:
                target = PurePosixPath(output["path"])
                reasons = []
                if path.name.casefold() == target.name.casefold():
                    reasons.append("same_basename")
                if path.name.casefold().startswith(target.stem.casefold() + "."):
                    reasons.append("same_stem")
                if target.suffix and path.suffix.casefold() == target.suffix.casefold():
                    reasons.append("same_suffix")
                if reasons:
                    matches.append({"output": output["path"], "reasons": reasons})
            # Exact answer copies can use unrelated names and formats. Size
            # is only a cheap hash prefilter; it is not an answer match itself.
            same_size = any(
                type(output.get("bytes")) is int and output["bytes"] == path.stat().st_size
                for output in outputs
            )
            if not packaged_test and not matches and not same_size:
                continue
            with path.open("rb") as stream:
                identity = hashlib.file_digest(stream, "sha256").hexdigest()
            for output in outputs:
                if output["sha256"] == identity:
                    matches.append({"output": output["path"], "reasons": ["identical_bytes"]})
            if not packaged_test and not matches:
                continue
            package_candidates += 1
            entry = {"distribution": distribution, "path": name, "sha256": identity}
            try:
                validate_manifest({"files": [entry]})
                removable = True
            except ValueError:
                removable = False
            candidate = {
                **entry,
                "bytes": path.stat().st_size,
                "matches": matches,
                "packaged_test_or_example": packaged_test,
                "eligible_for_declared_removal": removable,
            }
            if source is not None:
                # Test sources can hold answer constants despite having no
                # filename/hash relationship to an exported data artifact.
                # Keep their source relationship separate from output matches.
                candidate["source_import_matches"] = [
                    term
                    for term, pattern in source_patterns
                    if pattern.search(path.stem.casefold())
                ]
                candidate["source_import_group_matches"] = []
                if source_groups and path.suffix == ".py":
                    try:
                        code = path.read_bytes()
                        if hashlib.sha256(code).hexdigest() != identity:
                            raise ValueError("Candidate changed after hashing")
                        candidate["source_import_group_matches"] = shared_import_groups(
                            source_groups, code
                        )
                    except (SyntaxError, UnicodeError, ValueError) as error:
                        # Preserve the candidate and prior hints; unreadable
                        # source is a discovery gap, never a clearance claim.
                        candidate["source_import_group_inspection_error"] = type(error).__name__
            candidates.append(candidate)
        coverage.append(
            {
                "distribution": distribution,
                "installed_regular_files_inspected": package_inspected,
                "candidate_files": package_candidates,
                "dedicated_test_distribution_hint": dedicated_tests,
            }
        )
    candidates.sort(key=lambda row: (row["distribution"].casefold(), row["path"]))
    summary = {
        "scope": "Actual regular files recorded by installed distributions inside active site-packages. Candidate names/formats/tests are hints, not proof of answers or unused status; this is not an exhaustive filesystem or semantic audit.",
        "installed_files_inspected": inspected,
        "candidate_files": len(candidates),
        "distribution_coverage": sorted(coverage, key=lambda row: row["distribution"].casefold()),
        "priority_matches": [
            row
            for row in candidates
            if row.get("source_import_matches")
            or row.get("source_import_group_matches")
            or any(
                reason in {"same_basename", "same_stem", "identical_bytes"}
                for match in row["matches"]
                for reason in match["reasons"]
            )
        ],
    }
    if source is not None:
        summary["source_import_terms"] = source_terms
    return {"files": candidates, "summary": summary}


def validate_manifest(value, *, require_reason=False):
    if (
        not isinstance(value, dict)
        or set(value) != {"files"}
        or not isinstance(value["files"], list)
    ):
        raise ValueError("Dependency exclusions require a files array")
    seen = set()
    for item in value["files"]:
        required = {"distribution", "path", "sha256"}
        if require_reason:
            required.add("reason")
        if not isinstance(item, dict) or not required <= set(item) <= required | {"reason"}:
            raise ValueError(
                "Exclusions need distribution, path, sha256 and an unused-answer reason"
            )
        if not isinstance(item["distribution"], str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", item["distribution"]
        ):
            raise ValueError("Invalid installed distribution name")
        name = item["path"]
        if not isinstance(name, str):
            raise ValueError("Exclusion paths must be strings")
        path = PurePosixPath(name)
        if path.is_absolute() or not name or name == "." or ".." in path.parts or str(path) != name:
            raise ValueError("Exclusions need normalized distribution-relative file paths")
        if any(
            part.lower().endswith((".dist-info", ".egg-info"))
            or part.upper().startswith(("LICENSE", "COPYING", "COPYRIGHT", "NOTICE"))
            for part in path.parts
        ):
            raise ValueError("Do not remove distribution metadata or original notices")
        if not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("Exclusions require observed SHA-256 identities")
        if "reason" in item and (not isinstance(item["reason"], str) or not item["reason"].strip()):
            raise ValueError("Explain the matching answer evidence and why the file is unused")
        key = (re.sub(r"[-_.]+", "-", item["distribution"]).lower(), name)
        if key in seen:
            raise ValueError("Duplicate dependency exclusion")
        seen.add(key)
    return value


def apply_manifest(value, *, distribution=importlib.metadata.distribution, roots=None):
    validate_manifest(value)
    if roots is None:
        roots = [Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")]
    pending, seen = [], set()
    for item in value["files"]:
        installed = distribution(item["distribution"])
        if item["path"] not in {str(path) for path in installed.files or []}:
            raise ValueError("Exclusion is not an installed file of the declared distribution")
        path = Path(installed.locate_file(item["path"]))
        root = next((root for root in roots if path.is_relative_to(root)), None)
        if root is None or path.resolve() != path or not path.is_file():
            raise ValueError(
                "Only regular files inside the active installed environment may be excluded"
            )
        if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root):
            raise ValueError("Symlinked dependency assets cannot be excluded")
        if path in seen:
            raise ValueError("Two exclusions resolve to the same installed file")
        seen.add(path)
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != item["sha256"]:
            raise ValueError("Installed dependency asset differs from the observed identity")
        pending.append((path, {key: item[key] for key in ("distribution", "path", "sha256")}))
    # Verify all entries before changing any file; a rejected manifest deletes nothing.
    for path, _ in pending:
        path.unlink()
    if any(path.exists() for path, _ in pending):
        raise RuntimeError("Excluded dependency file remains present")
    return {"files": [item for _, item in pending], "excluded_files_absent": True}


def verify_absence(value, *, distribution=importlib.metadata.distribution, roots=None):
    """Recheck prior explicit removals without treating missing files as new removals."""
    validate_manifest(value)
    roots = roots or [Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")]
    files = []
    for item in value["files"]:
        installed = distribution(item["distribution"])
        # Distribution.files can filter out files that no longer exist. The
        # installed RECORD retains ownership after a verified deletion.
        record = installed.read_text("RECORD") if hasattr(installed, "read_text") else None
        owned = (
            {row[0] for row in csv.reader(record.splitlines()) if row}
            if record is not None
            else {str(path) for path in installed.files or []}
        )
        if item["path"] not in owned:
            raise ValueError("Excluded file is not owned by the declared distribution")
        path = Path(installed.locate_file(item["path"]))
        if not any(path.is_relative_to(root) for root in roots) or path.resolve() != path:
            raise ValueError("Excluded file escaped the installed environment")
        if path.exists() or path.is_symlink():
            raise ValueError("Previously excluded dependency asset is present")
        files.append({key: item[key] for key in ("distribution", "path", "sha256")})
    return {"files": files, "excluded_files_absent": True}


if __name__ == "__main__":
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Apply dependency exclusions using the task virtual environment")
    if sys.argv[1] in {"finalize", "verify-absence"}:
        request = json.loads(Path(sys.argv[2]).read_text())
        if sys.argv[1] == "finalize":
            apply_manifest(request["new_dependency_exclusions"])
        result = verify_absence(request["effective_dependency_exclusions"])
        Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n")
    elif sys.argv[1] == "inspect":
        result = inspect_assets(
            json.loads(Path(sys.argv[2]).read_text()),
            source=Path(sys.argv[4]).read_text() if len(sys.argv) > 4 else None,
        )
        Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result["summary"]))
    else:
        manifest = json.loads(Path(sys.argv[1]).read_text())
        result = apply_manifest(manifest)
        Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"files_removed": len(result["files"]), "excluded_files_absent": True}))
