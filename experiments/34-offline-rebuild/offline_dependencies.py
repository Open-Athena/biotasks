"""Opt-in static Python build-dependency plan; never execute project hooks."""
import hashlib
import re
import tomllib
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename


def build_plan(pyproject: bytes, *, base_commit: str):
    if not re.fullmatch(r'[0-9a-f]{40}', base_commit):
        raise ValueError('exact base commit required')
    data = tomllib.loads(pyproject.decode())
    target = data.get('project', {}).get('name')
    if not isinstance(target, str) or not target:
        raise ValueError('unsupported: missing static target distribution name')
    target = canonicalize_name(target)
    build = data.get('build-system', {})
    requirements = build.get('requires')
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('unsupported: no explicit build requirements')
    if build.get('backend-path'):
        raise ValueError('unsupported: in-tree build backend')
    for text in requirements:
        req = Requirement(text)
        if req.url:
            raise ValueError('unsupported: direct URL build dependency')
        if canonicalize_name(req.name) == target:
            raise ValueError('forbidden: target distribution dependency')
    return dict(base_commit=base_commit, target_distribution=target,
        pyproject_sha256=hashlib.sha256(pyproject).hexdigest(),
        build_requirements=requirements, build_backend=build.get('build-backend'),
        limitations=['Static requirements only; backend-requested dependencies may remain unavailable.',
            'Preparation must resolve for the runtime Python and platform.',
            'No source distributions, target-project wheels, or automatic repair.'])


def inspect_wheel(path: Path, *, target_distribution: str):
    """Check identity without importing/installing a wheel; retain byte digest."""
    name, version, _, tags = parse_wheel_filename(path.name)
    if name == canonicalize_name(target_distribution):
        raise ValueError('forbidden: target distribution wheel')
    if path.is_symlink() or path.stat().st_size > 128 * 1024**2:
        raise ValueError('unsupported wheel file')
    with ZipFile(path) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)):
            raise ValueError('duplicate wheel member')
        if any(n.startswith('/') or '..' in n.split('/') for n in names):
            raise ValueError('unsafe wheel path')
        metadata = [i for i in entries if i.filename.endswith('.dist-info/METADATA') and len(i.filename.split('/')) == 2]
        if len(metadata) != 1 or metadata[0].file_size > 1024**2:
            raise ValueError('invalid wheel metadata')
        message = BytesParser().parsebytes(archive.read(metadata[0]))
        if canonicalize_name(message.get('Name', '')) != name or message.get('Version') != str(version):
            raise ValueError('wheel identity mismatch')
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024**2), b''):
            digest.update(chunk)
    return dict(filename=path.name, name=name, version=str(version),
        tags=sorted(map(str, tags)), bytes=path.stat().st_size, sha256=digest.hexdigest())


def write_runtime_config(directory: Path):
    """Empty offline directory must fail dependency resolution, never use PyPI."""
    if not directory.is_absolute() or any(c.isspace() for c in str(directory)):
        raise ValueError('absolute cache path without whitespace required')
    return {'PIP_NO_INDEX': '1', 'PIP_FIND_LINKS': str(directory), 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
