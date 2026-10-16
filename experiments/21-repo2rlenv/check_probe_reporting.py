"""Offline regression for nested LiteLLM usage; model and validator are mocked."""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

from litellm.types.utils import Usage
from repo2rlenv.llm import LLMResponse

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe", root / "probe_glm_authoring_budget.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
usage = dict(
    Usage(
        prompt_tokens=7,
        completion_tokens=15,
        total_tokens=22,
        completion_tokens_details={"reasoning_tokens": 10},
    )
)
try:
    json.dumps(usage)
except TypeError:
    pass
else:
    raise AssertionError("Fixture must reproduce nested usage serialization failure")
mod.complete = lambda *a, **k: LLMResponse(
    content='{"issue":"Example observable bug","reason":"Fixture"}',
    usage=usage,
    prompt_tokens=7,
    completion_tokens=15,
)
mod.issue_violations = lambda *a: []

os.environ["BIOTASKS21_GLM_ENDPOINT"] = "https://example.invalid/v1"
os.environ["BIOTASKS21_GLM_KEY"] = "offline-fixture"
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "report.json"
    sys.argv = [
        "probe",
        "--output",
        str(out),
        "--request",
        str(root / "evidence/skbio-author-01/models/0e17fb52981f3f272561.request.json"),
        "--candidates",
        str(root / "evidence/skbio-smith-02/generation.json"),
    ]
    mod.main()
    r = json.loads(out.read_text())
    assert r["status"] == "passed"
    assert r["reasoning_tokens"] == 10
    assert r["non_reasoning_completion_tokens"] == 5
    assert (
        json.loads(out.with_suffix(".response.json").read_text())["usage"][
            "completion_tokens_details"
        ]["reasoning_tokens"]
        == 10
    )
print("PASS: nested LiteLLM usage, separate token counts, durable response; zero model calls")
