"""Offline execution check of the pinned tracer's caller-path adaptation."""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

from swe_flow_test_paths import adapt_driver

source = Path(sys.argv[1]).read_text()


def observed_target(text, caller):
    namespace = {"__name__": "offline_tracer"}
    exec(compile(text, "trace_driver.py", "exec"), namespace)
    tracer = namespace["CallTrace"]({"source_paths": ["Bio/SeqUtils"]})
    tracer.current = "synthetic"
    tracer.calls = 0
    tracer.deadline = time.monotonic() + 60
    tracer.records["synthetic"] = {"core_nodes": set(), "target_nodes": set(), "edges": set()}
    code = SimpleNamespace(
        co_filename="/workspace/Bio/SeqUtils/lcc.py", co_name="lcc_simp", co_firstlineno=1
    )
    caller_code = SimpleNamespace(co_filename=caller, co_name="test_count", co_firstlineno=1)
    tracer.profile(
        SimpleNamespace(f_code=code, f_back=SimpleNamespace(f_code=caller_code)), "call", None
    )
    assert len(tracer.records["synthetic"]["core_nodes"]) == 1
    return bool(tracer.records["synthetic"]["target_nodes"])


adapted = adapt_driver(source, ["Tests/test_SeqUtils.py"])
assert not observed_target(source, "/workspace/Tests/test_SeqUtils.py")
assert observed_target(adapted, "/workspace/Tests/test_SeqUtils.py")
assert not observed_target(adapted, "/workspace/Tests/test_other.py")
assert not observed_target(adapted, "/outside/Tests/test_SeqUtils.py")
assert observed_target(adapt_driver(source, ["skbio/tests"]), "/workspace/skbio/tests/test_api.py")
assert not observed_target(
    adapt_driver(source, ["skbio/tests"]), "/workspace/skbio/tests_extra/test_api.py"
)
for bad in (["../Tests"], ["/outside"], []):
    try:
        adapt_driver(source, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid roots accepted")
print(
    "PASS: native mismatch reproduced; configured file/directory roots bounded; zero target/model execution"
)
