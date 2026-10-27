import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT = ROOT / "experiments/19-repo2rlenv-notebook-pilot"
spec = importlib.util.spec_from_file_location(
    "restaging_admission", Path(__file__).with_name("runtime_admission.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
identity = json.loads((EXPERIMENT / "panel-rounds/103/runtime-identity.json").read_text())
BEFORE = subprocess.check_output(
    [
        "git",
        "show",
        identity["public_runtime_revision"] + ":" + module.PREFIX + "reference_setup.py",
    ],
    cwd=ROOT,
)
AFTER = (EXPERIMENT / "reference_setup.py").read_bytes()


def test_recorded_setup_addition_only():
    module.prove_setup_addition_only(BEFORE, AFTER)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"self.tests >= self.max_tests", b"False"),
        (b"self.tests += 1", b"self.tests += 0"),
        (b"await self.remote.network(True)", b"await self.remote.network(False)"),
        (b"after_restaging != hashes", b"False"),
        (b"Restaging changed its submitted candidate files", b"Accept changed candidate"),
    ],
)
def test_dispatch_budget_offline_and_immutability_changes_refused(old, new):
    assert old in AFTER
    with pytest.raises(AssertionError):
        module.prove_setup_addition_only(BEFORE, AFTER.replace(old, new))


def test_current_candidate_binds_actual_controls_and_original_source_families():
    runtime = json.loads(
        (EXPERIMENT / "panel-rounds/104/candidate-runtime-identity.json").read_text()
    )["runtime_files"]
    value = module.candidate_admission(ROOT, runtime)
    name = module.PREFIX + "reference_setup.py"
    assert module.check_source(value, name, identity["runtime_files"][name]).startswith(
        "explicit_tested"
    )
    with pytest.raises(AssertionError, match="unknown source"):
        module.check_source(value, name, "unreviewed")
    wrong = dict(runtime)
    wrong[module.PREFIX + "run_reference_setup.py"] = "unexpected"
    with pytest.raises(AssertionError):
        module.candidate_admission(ROOT, wrong)
