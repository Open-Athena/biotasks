"""Build a reviewable input bundle from an accepted setup run; no model call."""

import argparse
import hashlib
import json
from pathlib import Path

from package_inspection import inspection_context, package_catalog

INPUT_FILES = (
    "provenance.json",
    "inputs/original.py",
    "inputs/exports.py",
    "inputs/plan.json",
    "candidate/analysis.py",
    "trial/reference.py",
    "trial/source.diff",
    "candidate/inputs.json",
    "trial/inputs-before.json",
    "candidate/pyproject.toml",
    "trial/uv.lock",
    "trial/environment.txt",
    "trial/result.json",
    "result.json",
    "output-audit.json",
)


def specification_context(run, policy, *, inspect_packages=False, revision_context=None):
    """Check original evidence hashes and audit lineage, without executing it."""
    manifest = json.loads((run / "artifact-manifest.json").read_text())
    originals = {item["path"]: item for item in manifest["files"]}
    files = {}
    hashes = {}
    for path in INPUT_FILES:
        content = (run / path).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        # The audit and provenance snapshot were preserved separately from
        # the setup worker's original manifest; pin them in this input bundle.
        if path not in {"output-audit.json", "provenance.json"}:
            record = originals[path]
            if digest != record["sha256"] or len(content) != record["bytes"]:
                raise ValueError(f"Original evidence changed: {path}")
        hashes[path] = digest
        files[path] = json.loads(content) if path.endswith(".json") else content.decode()

    trial = files["trial/result.json"]
    if (
        trial["status"] != "reference_executed"
        or trial["execution"]["exit_code"] != 0
        or trial["execution"]["timed_out"]
        or files["result.json"]["status"] != "reference_executed_requires_review"
    ):
        raise ValueError("Specification requires a passing reference test")
    observed = trial["artifacts"]["artifacts"]
    audit = files["output-audit.json"]["outputs"]
    expected = {item["path"]: (item["sha256"], item["bytes"]) for item in observed}
    audited = {item["file"]: (item["sha256"], item["bytes"]) for item in audit}
    declared = [item["path"] for item in files["inputs/plan.json"]["artifacts"]]
    if (
        len(expected) != len(observed)
        or len(audited) != len(audit)
        or expected != audited
        or len(set(declared)) != len(declared)
        or set(declared) != set(expected)
        or not all(item["exists"] for item in observed)
        or not all(item["download_hash_verified"] for item in audit)
    ):
        raise ValueError("Declared exports, executed outputs and audited files disagree")
    context = {
        "files": {path: value for path, value in files.items() if path != "trial/uv.lock"},
        "file_sha256": hashes,
        "retained_evidence": {
            "trial/uv.lock": {
                "sha256": hashes["trial/uv.lock"],
                "bytes": originals["trial/uv.lock"]["bytes"],
                "reason": "Full lock retained as evidence; exact resolved package versions are supplied in trial/environment.txt. Wheel URLs and hashes are omitted from model context.",
            }
        },
        "task_policy": policy,
        "evidence_boundary": (
            "One passing reference test and structural output audit. No full data tables "
            "in this context, no independent scientific reproduction, repeatability "
            "measurement, calibrated grader or solver evidence. No tools in this pass."
        ),
    }
    if revision_context is not None:
        context["revision_context"] = revision_context
    if inspect_packages:
        context["package_inspection"] = inspection_context(
            package_catalog(files["trial/uv.lock"], files["trial/environment.txt"])
        )
        context["evidence_boundary"] = context["evidence_boundary"].replace(
            "No tools in this pass.", "Read-only package-source tools are available."
        )
    return context


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    context = specification_context(args.run, json.loads(args.policy.read_text()))
    args.output.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n")
