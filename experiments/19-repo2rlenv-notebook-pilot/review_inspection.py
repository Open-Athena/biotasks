"""Read-only reviewer evidence from the verified execution snapshot."""

import hashlib
import json
from pathlib import Path

from package_inspection import (
    PACKAGE_TOOLS,
    PackageInspection,
    inspection_context,
    package_catalog,
)
from reference_inspection import REFERENCE_TOOLS, ReferenceInspection, reference_catalog
from reference_replay import sha256


class ReviewInspection:
    def __init__(self, snapshot, root, deadline):
        self.root, self.deadline, self.executions = root, deadline, None
        reference = snapshot["directory"]
        evidence = {}
        identities = {}
        for name in ("trial/uv.lock", "trial/environment.txt"):
            path = reference / name
            digest = sha256(path)
            if digest != snapshot["hashes"][name]:
                raise ValueError("Reviewer environment evidence identity changed: " + name)
            evidence[name] = path.read_text()
            identities[name] = digest
        packages = package_catalog(evidence["trial/uv.lock"], evidence["trial/environment.txt"])
        references = reference_catalog(snapshot["outputs"])
        # Use the controller's restored original outputs, never a submission,
        # independently generated outputs, or a model-selected filesystem root.
        outputs = Path(
            snapshot.get(
                "restored_outputs_root",
                "/work/grading-inputs/reference-replay/replay/trials/1/outputs",
            )
        )
        self.packages = PackageInspection(packages, root / "package-sources", deadline)
        self.references = ReferenceInspection(outputs, references["files"], deadline)
        self.context = {
            "package_inspection": inspection_context(packages, evidence["trial/environment.txt"]),
            "reference_inspection": references,
            "inspection_evidence_sha256": identities,
        }
        (root / "identities.json").write_text(json.dumps(self.context, indent=2) + "\n")

    def refresh_execution_evidence(self, roots):
        from execution_inspection import ExecutionInspection

        observed = ExecutionInspection(roots, self.deadline)
        if self.executions is not None:
            for name, row in self.executions.catalog.items():
                if row["available"] and observed.catalog.get(name) != row:
                    raise ValueError("Previously completed reviewer evidence changed")
        manifest = {
            "operations": observed.catalog,
            "scope": (
                "Prior recorded commands/output, including author diagnostics; not extra fresh "
                "acceptance controls or proof of scientific correctness. Missing/incomplete "
                "records remain evidence gaps. Search absence concerns only this catalog. "
                "Read both command and output before treating a printed claim as an observation."
            ),
        }
        raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        identity = hashlib.sha256(raw).hexdigest()
        directory = self.root / "execution-manifests"
        directory.mkdir(exist_ok=True)
        path = directory / (identity + ".json")
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError("Reviewer evidence manifest identity changed")
        else:
            path.write_bytes(raw)
        self.executions = observed
        self.context["execution_inspection"] = {**manifest, "manifest_sha256": identity}
        (self.root / "identities.json").write_text(json.dumps(self.context, indent=2) + "\n")

    @property
    def tools(self):
        from execution_inspection import EXECUTION_TOOLS

        return [*PACKAGE_TOOLS, *REFERENCE_TOOLS, *(EXECUTION_TOOLS if self.executions else [])]

    @property
    def handlers(self):
        return {
            **self.packages.handlers,
            **self.references.handlers,
            **(self.executions.handlers if self.executions else {}),
        }
