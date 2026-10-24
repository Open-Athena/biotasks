"""Reporting-only prototype for already-loaded, explicitly named Python modules.

Run in the test sandbox. Never import target modules or execute their code. This
is not a grading gate, a project/import mapping, or a complete code identity proof.
"""

import hashlib
import importlib.metadata
import marshal
import os
import sys
import types
from pathlib import Path
from urllib.parse import urlsplit


def code_tree(code):
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from code_tree(constant)


def digest_code(code):
    return hashlib.sha256(marshal.dumps(code)).hexdigest()


def loaded_functions(module):
    namespace = vars(module)
    found = []
    for name, value in list(namespace.items()):
        if isinstance(value, types.FunctionType) and value.__globals__ is namespace:
            found.append((name, value))
        elif isinstance(value, type) and vars(value).get("__module__") == module.__name__:
            for member, method in list(vars(value).items()):
                if isinstance(method, (staticmethod, classmethod)):
                    method = method.__func__
                if isinstance(method, types.FunctionType) and method.__globals__ is namespace:
                    found.append((name + "." + member, method))
        if len(found) > 128:
            raise ValueError("Function observation bound exceeded")
    return found


def module_snapshot(root, name):
    module = sys.modules.get(name)
    if module is None:
        return {
            "module": name,
            "origin": "unobserved",
            "reason": "Not loaded; target not imported by observer",
        }
    row = {"module": name, "declared_file": vars(module).get("__file__")}
    try:
        if row["declared_file"] is None:
            return dict(row, origin="ambiguous", reason="No single source file")
        path = Path(row["declared_file"]).resolve(strict=True)
        row.update(
            realpath=str(path), origin="checkout" if path.is_relative_to(root) else "foreign"
        )
        if path.suffix != ".py" or not path.is_file() or path.stat().st_size > 2 * 1024**2:
            return dict(row, origin="ambiguous", reason="Not bounded ordinary Python source")
        source = path.read_bytes()
        row["source_sha256"] = hashlib.sha256(source).hexdigest()
        current = compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize)
        by_key = {(c.co_qualname, c.co_firstlineno): c for c in code_tree(current)}
        functions = []
        for label, function in loaded_functions(module):
            code = function.__code__
            candidate = by_key.get((code.co_qualname, code.co_firstlineno))
            functions.append(
                {
                    "name": label,
                    "qualname": code.co_qualname,
                    "loaded_code_filename": code.co_filename,
                    "loaded_code_sha256": digest_code(code),
                    "current_source_code_sha256": digest_code(candidate) if candidate else None,
                    "matches_current_source": candidate is not None and code == candidate,
                }
            )
        row["loaded_functions"] = functions
        row["function_comparison"] = (
            "unobserved"
            if not functions
            else "matches_observed_functions"
            if all(f["matches_current_source"] for f in functions)
            else "mismatch"
        )
    except Exception as error:
        row.update(origin="ambiguous", error=type(error).__name__)
    return row


def snapshot(root, project, modules, phase):
    root = Path(root).resolve(strict=True)
    if len(modules) > 16 or len(set(modules)) != len(modules):
        raise ValueError("Expected at most16 unique requested modules")
    try:
        distribution = importlib.metadata.distribution(project)
        # Do not copy remote/direct URL values that could contain credentials.
        direct = distribution.read_text("direct_url.json")
        import json

        direct = json.loads(direct) if direct else None
        metadata = {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
            "editable": bool(direct and direct.get("dir_info", {}).get("editable")),
            "direct_url_scheme": urlsplit(direct["url"]).scheme
            if direct and "url" in direct
            else None,
        }
    except (importlib.metadata.PackageNotFoundError, ValueError) as error:
        metadata = {"error": type(error).__name__}
    return {
        "phase": phase,
        "pid": os.getpid(),
        "project": project,
        "distribution": metadata,
        "modules": [module_snapshot(root, name) for name in modules],
        "targets_imported_by_observer": False,
        "reward_or_git_identity_verified": False,
    }
