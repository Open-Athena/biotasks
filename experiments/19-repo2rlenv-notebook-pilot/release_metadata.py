"""Explicit per-release metadata; never reuse another notebook's attribution."""

import hashlib
import json
from pathlib import Path


def load_release_metadata(config):
    metadata = config.get("release_metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Explicit release_metadata is required")
    for key in ("repo_id", "title", "description", "methodology", "licenses_file", "seed_file"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"Explicit release metadata {key} is required")
    citations = metadata.get("citations")
    if (
        not isinstance(citations, list)
        or not citations
        or any(not isinstance(value, str) or not value.strip() for value in citations)
    ):
        raise ValueError("Explicit release citations are required")
    licenses = json.loads(Path(metadata["licenses_file"]).read_text())
    if not isinstance(licenses, dict) or not licenses:
        raise ValueError("Source-license evidence must be a nonempty object")
    source_license = licenses.get("notebook_license", {})
    if not isinstance(source_license, dict):
        raise ValueError("Source-license evidence must be an object")
    if "sha256" in source_license:
        text = source_license.get("text")
        if not isinstance(text, str):
            raise ValueError("Hashed source-license evidence needs text")
        text = text.encode()
        if hashlib.sha256(text).hexdigest() != source_license["sha256"]:
            raise ValueError("Source-license text differs from its recorded hash")
    seeds = json.loads(Path(metadata["seed_file"]).read_text())
    if not isinstance(seeds, list) or len(seeds) != 1:
        raise ValueError("A single explicitly selected release seed is required")
    provenance = seeds[0].get("provenance") if isinstance(seeds[0], dict) else None
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("Selected release seed needs provenance")
    if "source_provenance" in licenses and licenses["source_provenance"] != provenance:
        raise ValueError("Selected seed differs from the bundled source provenance")
    return metadata, licenses, provenance


def verify_bundle_licenses(task, licenses):
    recorded = json.loads((Path(task) / "environment/SOURCE-LICENSES.json").read_text())
    if recorded != licenses:
        raise ValueError("Release attribution differs from the validated task bundle")
