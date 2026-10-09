"""Exercise export selection without importing the remote Iris runtime."""

import ast
import os
import tempfile
import unittest
from pathlib import Path

source = Path(__file__).with_name("zcode_smoke.py")
tree = ast.parse(source.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "export_files")
namespace = {"os": os, "Path": Path}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
export_files = namespace["export_files"]


class ExportChecks(unittest.TestCase):
    def test_marker_based_pruning_preserves_task_and_scientific_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [
                ".venv-ref/example-1.dist-info/METADATA",
                ".venv-ref/example/module.py",
                "unusual-env-name/pyvenv.cfg",
                "unusual-env-name/bin/python",
                "reference/results.json",
                "task/environment/.venv/example-1.dist-info/METADATA",
                "task/tests/expected.json",
                "review/report.json",
            ]
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("evidence")
            (root / "outside-link").symlink_to("/etc/passwd")
            selected, excluded = export_files(root)
            self.assertEqual(
                {str(p.relative_to(root)) for p in selected},
                set(paths[4:]),
            )
            self.assertEqual(
                {entry["path"] for entry in excluded},
                {".venv-ref", "unusual-env-name"},
            )


if __name__ == "__main__":
    unittest.main()
