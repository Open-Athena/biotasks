"""Exercise real synthetic module origins; no biological imports or network."""

import importlib
import json
import shutil
import sys
from pathlib import Path

from collect import collect


def main():
    base = Path(__file__).parent.resolve()
    scratch = base / "inputs-private" / "edge-001"
    scratch.mkdir(exist_ok=False)
    checkout = scratch / "checkout"
    outside = scratch / "outside"
    checkout.mkdir()
    outside.mkdir()
    reports = {}
    names = []
    original_path = sys.path[:]
    original_policy = sys.dont_write_bytecode

    def report(key, module, expected):
        names.append(module)
        importlib.invalidate_caches()
        value = collect(checkout, "biotasks56-no-such-distribution", [module])
        assert value["binding"] == expected, value
        assert value["git_revision_or_reward_verified"] is False
        assert value["installation_or_sys_path_changed_by_collector"] is False
        assert sys.dont_write_bytecode == original_policy
        reports[key] = value

    try:
        sys.path[:0] = [str(outside), str(checkout)]
        (checkout / "bt56_inside.py").write_text("ORIGIN = 'checkout'\n")
        report("ordinary_checkout", "bt56_inside", "checkout")
        assert reports["ordinary_checkout"]["distribution"]["error"] == "PackageNotFoundError"

        (outside / "bt56_forward.py").symlink_to(checkout / "bt56_inside.py")
        report("outside_declared_path_real_checkout", "bt56_forward", "checkout")

        (outside / "bt56_release.py").write_text("ORIGIN = 'foreign'\n")
        (checkout / "bt56_escape.py").symlink_to(outside / "bt56_release.py")
        report("checkout_declared_path_real_foreign", "bt56_escape", "foreign")

        (checkout / "bt56_namespace").mkdir()
        report("namespace_ambiguous", "bt56_namespace", "ambiguous")
        report("missing_ambiguous", "bt56_missing", "ambiguous")

        (checkout / "bt56_broken.py").write_text("raise RuntimeError('synthetic import failure')\n")
        report("import_failure_ambiguous", "bt56_broken", "ambiguous")

        (checkout / "bt56_oversized.py").write_text("#" + "x" * (2 * 1024**2))
        report("oversized_ambiguous", "bt56_oversized", "ambiguous")

        (outside / "bt56_sticky.py").write_text("ORIGIN = 'first foreign import'\n")
        (checkout / "bt56_sticky.py").write_text("ORIGIN = 'checkout'\n")
        importlib.import_module("bt56_sticky")
        sys.path.remove(str(outside))
        importlib.invalidate_caches()
        report("already_loaded_foreign_stays_foreign", "bt56_sticky", "foreign")
        assert not list(scratch.rglob("*.pyc"))
    finally:
        sys.path[:] = original_path
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.pop("bt56_sticky", None)
        shutil.rmtree(scratch)
    result = {
        "synthetic": True,
        "cases": reports,
        "passed": len(reports),
        "scratch_removed": not scratch.exists(),
        "new_model_calls": 0,
        "new_native_jobs": 0,
        "limits": [
            "Distribution-to-module mapping is not verified; missing metadata does not establish package validity.",
            "A checkout origin is not verified Git revision, patch execution, reward or native pytest-process identity.",
            "Imports may have side effects; biological inspection belongs in the target sandbox.",
            "Namespace, native extension and rebuilt-code policies are not implemented.",
        ],
    }
    (base / "edge-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": len(reports), "scratch_removed": result["scratch_removed"]}))


if __name__ == "__main__":
    main()
