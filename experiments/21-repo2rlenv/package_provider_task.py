"""Deterministic flat-file transfer for a Harbor task, preserving bytes and modes."""
import hashlib
import gzip
import json
import tarfile
from pathlib import Path


def pack(task, archive):
    records = {}
    with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed, tarfile.open(fileobj=compressed, mode='w') as target:
        for path in sorted(task.rglob('*')):
            if path.is_symlink():
                raise ValueError('Linked task asset requires separate review')
            if not path.is_file():
                continue
            name = str(path.relative_to(task))
            records[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'mode': path.stat().st_mode & 0o777}
            info = target.gettarinfo(str(path), arcname='task/' + name)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            with path.open('rb') as source:
                target.addfile(info, source)
    return {'files': records, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}


def unpack(archive, manifest, destination):
    data = json.loads(manifest.read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == data['archive_sha256']
    with tarfile.open(archive) as source:
        members = source.getmembers()
        assert {m.name for m in members} == {'task/' + n for n in data['files']}
        assert len(members) == len(data['files'])
        assert sum(m.size for m in members) <= 4 * 1024**2
        for member in members:
            name = Path(member.name)
            assert member.isfile() and not name.is_absolute() and '..' not in name.parts
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(source.extractfile(member).read())
            key = str(name.relative_to('task'))
            target.chmod(data['files'][key]['mode'])
            assert hashlib.sha256(target.read_bytes()).hexdigest() == data['files'][key]['sha256']
