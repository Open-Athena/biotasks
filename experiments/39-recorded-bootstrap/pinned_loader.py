"""Unchanged AST loader helpers adopted from the executed #29 replay."""
import ast


def load_functions(path, names, namespace):
    """Compile selected original AST nodes with no source rewrite."""
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)


def load_post_checks(path, namespace):
    """Exact original smoke/git statements; no model or other bootstrap stages."""
    tree = ast.parse(path.read_text())
    nodes = sorted([n for n in ast.walk(tree) if isinstance(n, ast.stmt) and n.lineno in (630, 631, 650, 651)], key=lambda n: n.lineno)
    assert len(nodes) == 4
    assert [n.end_lineno for n in nodes] == [630, 640, 650, 665]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
