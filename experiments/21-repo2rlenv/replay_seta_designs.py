"""Reuse frozen designs in the native SETA builder without another design call.

The callback changes only design retrieval. Native materialization, repair,
baseline/oracle trials and export remain in terminal.runner.run_synthesis.
Original model text is returned unchanged, including its formatting defects.
"""

import hashlib
import json
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.seta_seed2synth.recipe import TaskDesign


def saved_designer(path: Path, expected_sha256: str):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Saved design archive changed")
    payload = json.loads(raw)
    if payload.get("stage") != "design_only":
        raise ValueError("Expected design-only evidence")
    records = {}
    for record in payload["records"]:
        key = record["seed_sha256"]
        if key in records:
            raise ValueError("Duplicate saved seed fingerprint")
        if record["status"] == "designed":
            records[key] = record

    def design(seed, *, model, ledger, receipt, operation_id, resume):
        digest = hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()
        if digest not in records or records[digest]["seed_id"] != seed["id"]:
            raise ValueError("No successful design for this exact seed")
        result = TaskDesign.model_validate(records[digest]["design"])
        # This is a replay receipt, never a claim of another model request.
        save_record(receipt, {
            "stage": "saved_design_replay", "model_calls": 0,
            "source_sha256": expected_sha256, "seed_sha256": digest,
            "operation_id": operation_id, "text_normalized": False,
        })
        return result

    return design
