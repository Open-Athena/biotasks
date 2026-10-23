"""Read-only reviewer evidence from the verified execution snapshot."""

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

    @property
    def tools(self):
        return [*PACKAGE_TOOLS, *REFERENCE_TOOLS]

    @property
    def handlers(self):
        return {**self.packages.handlers, **self.references.handlers}
