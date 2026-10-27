import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[3]
SOURCE = "experiments/19-repo2rlenv-notebook-pilot/review_packet.py"
PROMPT = "src/biotasks/prompts/notebook-grader-review.md"
BASELINE = "afddb9f671ae57412dd0eb3a3292e9cfae3123a8"
spec = importlib.util.spec_from_file_location(
    "batch_source_proof_fixture", HERE / "source_proof.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BEFORE = subprocess.check_output(["git", "show", BASELINE + ":" + SOURCE], cwd=ROOT)
AFTER = (ROOT / SOURCE).read_bytes()
OLD_PROMPT = subprocess.check_output(["git", "show", BASELINE + ":" + PROMPT], cwd=ROOT)
NEW_PROMPT = (ROOT / PROMPT).read_bytes()


def test_actual_extension_preserves_original_reader_and_prompt():
    module.prove_readonly_extension(BEFORE, AFTER)
    module.prove_prompt_only(OLD_PROMPT, NEW_PROMPT)


@pytest.mark.parametrize(
    "old,new",
    [
        (b'if len(raw) != row["bytes"]', b'if False and len(raw) != row["bytes"]'),
        (b"if time.time() >= self.deadline:", b"if False:"),
        (b"return result\n", b"return {}\n"),
        (b"response = json.loads(await read(**request))", b'response = {"passed": True}'),
        (
            b"async def batch(requests):\n            self.remaining()",
            b"async def batch(requests):\n            self.deadline += 60\n            self.remaining()",
        ),
        (b'"read_review_evidence_batch",', b'"shell",'),
    ],
)
def test_changed_identity_deadline_content_or_execution_permission_is_refused(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_readonly_extension(BEFORE, AFTER.replace(old, new))


def test_prompt_cannot_drop_an_existing_evidence_requirement():
    with pytest.raises(AssertionError):
        module.prove_prompt_only(
            OLD_PROMPT,
            NEW_PROMPT.replace(b"Inspect every supplied hint", b"Ignore every supplied hint"),
        )
