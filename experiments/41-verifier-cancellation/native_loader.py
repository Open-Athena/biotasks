"""Load exact selected source AST; callers explicitly supply transport stubs."""
import ast
import hashlib
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path,name,namespace,owner=None):
    text=Path(path).read_text();tree=ast.parse(text)
    parent=tree if owner is None else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==owner)
    node=next(n for n in parent.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==name)
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),namespace)
    return dict(path=str(path),sha256=sha(path),symbol=(owner+'.' if owner else '')+name,line=node.lineno,end_line=node.end_lineno,
        symbol_source_sha256=hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest())
