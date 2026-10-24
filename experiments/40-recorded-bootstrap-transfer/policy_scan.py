"""Unchanged bounded public artifact inspector adopted from #39."""
import io
import re
import tarfile
from common import safe,content_sha

LIMIT=32*1024**2

SECRET=re.compile(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')

def inspect(raw,kind=None,depth=0):
    assert len(raw)<=LIMIT and depth<=3
    if not kind:
        raw.decode('utf-8')
        assert not SECRET.search(raw) and b'GIT binary patch' not in raw and b'data:image/' not in raw
        assert b'\x00' not in raw
        return None
    if kind=='tar.zst':
        import zstandard
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as stream:expanded=stream.read(LIMIT+1)
        assert len(expanded)<=LIMIT
        archive=tarfile.open(fileobj=io.BytesIO(expanded),mode='r:')
    else:archive=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')
    rows=[];names=set();total=0
    with archive:
        for member in archive:
            safe(member.name)
            if member.isdir():continue
            assert member.isfile() and member.name not in names and 0<=member.size<8*1024**2
            names.add(member.name);total+=member.size;assert total<=LIMIT
            value=archive.extractfile(member).read();assert len(value)==member.size
            nested='tar.gz' if member.name.endswith('.tar.gz') else None
            children=inspect(value,nested,depth+1)
            row=dict(path=member.name,bytes=member.size,mode=oct(member.mode),sha256=content_sha(value))
            if children is not None:row['members']=children
            rows.append(row)
    return rows
