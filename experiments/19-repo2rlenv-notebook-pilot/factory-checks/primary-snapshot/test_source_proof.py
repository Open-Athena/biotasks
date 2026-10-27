"""Transport admission must refuse unrelated policy or scientific changes."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "primary_snapshot_proof", Path(__file__).with_name("prove_boundary.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize(
    "name,check",
    [("iris_bootstrap.py", module.prove_bootstrap), ("run_autonomous.py", module.prove_controller)],
)
def test_only_declared_transport_change_is_admitted(name, check):
    check(module.original(name), (module.EXPERIMENT / name).read_bytes())


@pytest.mark.parametrize(
    "before,after",
    [
        ("snapshot=False", "snapshot=True"),
        ("max_workers=4", "max_workers=5"),
        ('"BIOTASKS_EXPORT_IDLE_SECONDS", "600"', '"BIOTASKS_EXPORT_IDLE_SECONDS", "601"'),
    ],
)
def test_changed_default_concurrency_or_deadline_is_not_transport_only(before, after):
    current = (module.EXPERIMENT / "iris_bootstrap.py").read_text()
    assert before in current
    with pytest.raises(AssertionError):
        module.prove_bootstrap(
            module.original("iris_bootstrap.py"), current.replace(before, after, 1)
        )


@pytest.mark.parametrize(
    "before,after",
    [
        ("snapshot=True", "snapshot=False"),
        ('"/autonomous-snapshot"', '"/unbound-prefix"'),
        ('status="validated", task_directory=', 'status="rejected", task_directory='),
        (
            "deadline=self.deadline,\n                snapshot=True",
            "deadline=self.deadline + 1,\n                snapshot=True",
        ),
    ],
)
def test_changed_outcome_deadline_or_unbound_archive_is_not_admitted(before, after):
    current = (module.EXPERIMENT / "run_autonomous.py").read_text()
    assert before in current
    with pytest.raises(AssertionError):
        module.prove_controller(
            module.original("run_autonomous.py"), current.replace(before, after, 1)
        )
