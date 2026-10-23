"""Apply worker-declared unused answer-file exclusions inside the task environment.

The worker establishes answer relevance and unused status; this helper checks
exact installed ownership/content and records deletion. It never selects files.
"""

import hashlib
import importlib.metadata
import json
import re
import sys
import sysconfig
from pathlib import Path, PurePosixPath


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


if __name__ == "__main__":
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Apply dependency exclusions using the task virtual environment")
    manifest = json.loads(Path(sys.argv[1]).read_text())
    result = apply_manifest(manifest)
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files_removed": len(result["files"]), "excluded_files_absent": True}))
