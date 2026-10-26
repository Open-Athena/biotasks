"""Inspect an archived review input through the new lossless packet, no execution."""

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
from review_packet import ReviewPacket, encode  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input", type=Path)
parser.add_argument("--packet-root", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
raw = args.input.read_bytes()
original = json.loads(raw)
packet = ReviewPacket(args.packet_root, original, time.time() + 60)
assert packet.reconstruct() == original
assert encode(packet.reconstruct()) == encode(original)
assert args.input.read_bytes() == raw
# The review admission callback must remain exactly the original code, not an
# alternative implementation of its source/fixture/control acceptance rules.
repository = EXPERIMENT.parents[1]
relative = EXPERIMENT.relative_to(repository) / "grading_session.py"
baseline = subprocess.check_output(
    ["git", "show", "dc307217:" + str(relative)], cwd=repository, text=True
)


def admission(source):
    return next(
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "validate_review"
    )


assert ast.dump(admission(baseline), include_attributes=False) == ast.dump(
    admission((EXPERIMENT / "grading_session.py").read_text()), include_attributes=False
)
result = {
    "scope": "Offline packet construction/readback against a captured review input. No model, biological computation, grading, reward or original artifact change.",
    "source_input_sha256": hashlib.sha256(raw).hexdigest(),
    "source_input_file_bytes": len(raw),
    "original_json_value_bytes": len(encode(original)),
    "model_context_json_value_bytes": len(encode(packet.model_context)),
    "all_original_json_values_reconstructed": True,
    "original_input_unchanged": True,
    "all_fields_inspectable": sorted(packet.catalog),
    "inline_fields": sorted(set(packet.model_context) - {"review_evidence"}),
    "packet_context_sha256": packet.context_sha256,
    "packet_manifest_sha256": packet.manifest_sha256,
    "controller_admission_callback_ast_unchanged": True,
    "actual_provider_acceptance_tested": False,
    "qualified_scientific_task": False,
    "new_model_calls": 0,
    "new_jobs_or_sandboxes": 0,
}
args.result.write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {k: v for k, v in result.items() if k not in {"all_fields_inspectable", "inline_fields"}}
    )
)
