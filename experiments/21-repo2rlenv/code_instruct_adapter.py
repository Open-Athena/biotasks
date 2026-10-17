"""Explicit package mapping and candidate cap for the pinned native recipe.

This changes preparation only. Authoring, decontamination, test-strength checks,
reference validation, and export still use the native implementation.
"""

import hashlib
import inspect
import textwrap
from contextlib import contextmanager
from unittest.mock import patch

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines import code_instruct

PACKAGE_MAPPING = {"biopython": "Bio", "scikit-bio": "skbio"}


@contextmanager
def adapted_code_instruct(output):
    original = code_instruct.CodeInstructPipeline.run
    source = textwrap.dedent(inspect.getsource(original))
    old = "if candidates_seen >= self.options.limit * 5:"
    new = "if candidates_seen >= min(10, self.options.limit * 5):"
    if source.count(old) != 1:
        raise ValueError("Pinned native candidate loop changed; inspect before adapting")
    adapted = source.replace(old, new)
    namespace = {}
    exec(compile(adapted, "code-instruct-bounded-run.py", "exec"), code_instruct.__dict__, namespace)

    def detect_package(root, repo_name):
        package = PACKAGE_MAPPING.get(repo_name)
        if package is None:
            raise ValueError("Repository outside this experiment's Python panel")
        if not any((root / prefix / package / "__init__.py").is_file() for prefix in (".", "src")):
            raise ValueError("Explicit package mapping is absent from the checkout")
        return package

    save_record(output / "code-instruct-adaptation.json", {
        "stage": "explicit_recipe_adaptation",
        "package_mapping": PACKAGE_MAPPING,
        "max_candidates": 10,
        "native_run_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "adapted_run_sha256": hashlib.sha256(adapted.encode()).hexdigest(),
        "changes": ["Require explicit existing package", "Bound native seed candidates to ten"],
        "model_settings_changed": False,
        "validation_changed": False,
    })
    with (
        patch.object(code_instruct, "detect_repo_package", detect_package),
        patch.object(code_instruct.CodeInstructPipeline, "run", namespace["run"]),
    ):
        yield
