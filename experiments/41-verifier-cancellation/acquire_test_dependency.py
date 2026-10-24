"""Stage only the original Harbor run's Tenacity version for isolated checks."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def fetch(url,path,limit):
    with urllib.request.urlopen(url,timeout=60) as source,Path(path).open('wb') as dest:
        total=0
        while chunk:=source.read(65536):total+=len(chunk);assert total<=limit;dest.write(chunk)


def main():
    directory=ROOT/'inputs-private/check-dependency';directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    metadata=directory/'pypi-metadata.json';url='https://pypi.org/pypi/tenacity/9.2.1/json';fetch(url,metadata,1024**2)
    data=json.loads(metadata.read_text());assert data['info']['version']=='9.2.1'
    wheel=next(r for r in data['urls'] if r['filename']=='tenacity-9.2.1-py3-none-any.whl')
    assert wheel['url'].startswith('https://files.pythonhosted.org/packages/') and wheel['size']<1024**2
    archive=directory/wheel['filename'];fetch(wheel['url'],archive,1024**2)
    assert archive.stat().st_size==wheel['size'] and sha(archive)==wheel['digests']['sha256']
    source=directory/'source';source.mkdir(exist_ok=True);files=[];expanded=0
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            name=PurePosixPath(entry.filename);assert not name.is_absolute() and '..' not in name.parts
            if entry.is_dir() or not (entry.filename.endswith('.py') or entry.filename.endswith('.dist-info/METADATA') or '/licenses/' in entry.filename):continue
            expanded+=entry.file_size;assert entry.file_size<1024**2 and expanded<2*1024**2 and ((entry.external_attr>>16)&0o170000)!=0o120000
            raw=z.read(entry);raw.decode('utf8');target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            files.append(dict(path=entry.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    result=dict(name='tenacity',version='9.2.1',source_metadata_url=url,metadata_sha256=sha(metadata),wheel_url=wheel['url'],wheel_sha256=sha(archive),wheel_bytes=wheel['size'],source_files=files,
        version_provenance=dict(source_issue=39,member='harbor066-freeze.txt',member_sha256='a4f22919e20e8af53295edf3da04e82d660edb6db8f5397e1aa4daffc91c3a03'),
        installed_into_global_or_project_environment=False,purpose='Isolated dependency for native AST checks only; not an original task dependency change',model_calls=0,remote_jobs=0)
    (ROOT/'test-dependency-acquisition.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(version='9.2.1',wheel_bytes=wheel['size'],source_files=len(files),global_install=False)))


if __name__=='__main__':main()
