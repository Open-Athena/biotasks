import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[3]
PROTOCOL = "experiments/19-repo2rlenv-notebook-pilot/specification_protocol.py"
PROMPT = "src/biotasks/prompts/notebook-specification-review.md"
BASELINE = "c97ff1b2ca0b0c71aa80826457310f92417b1529"
spec = importlib.util.spec_from_file_location(
    "citation_source_proof_fixture", HERE / "source_proof.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BEFORE = subprocess.check_output(["git", "show", BASELINE + ":" + PROTOCOL], cwd=ROOT)
AFTER = (ROOT / PROTOCOL).read_bytes()
OLD_PROMPT = subprocess.check_output(["git", "show", BASELINE + ":" + PROMPT], cwd=ROOT)
NEW_PROMPT = (ROOT / PROMPT).read_bytes()


def test_actual_diagnostic_and_prompt_changes_are_bounded():
    module.prove_diagnostics_only(BEFORE, AFTER)
    module.prove_prompt_only(OLD_PROMPT, NEW_PROMPT)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"item.quote not in", b"False and item.quote not in"),
        (b"if item.path not in", b"if False and item.path not in"),
        (b"return review", b"return None"),
        (b'if (self.disposition == "ready") != (not self.findings):', b"if False:"),
    ],
)
def test_changed_acceptance_or_schema_cannot_be_called_a_diagnostic_change(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_diagnostics_only(BEFORE, AFTER.replace(old, new))


def test_prompt_cannot_erase_blockers_or_change_an_unrelated_policy():
    with pytest.raises(AssertionError):
        module.prove_prompt_only(
            OLD_PROMPT, NEW_PROMPT.replace(b"without deleting", b"by deleting")
        )
