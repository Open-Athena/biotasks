"""Inspect the exact already pinned wheel without installing or executing it."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent
LIMIT=16*1024**2


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    pin_path=ROOT.parents[2]/'39/experiments/39-recorded-bootstrap/control-pins.json'
    pins=json.loads(pin_path.read_text());assert pins['harbor_version']=='0.6.6'
    url=pins['harbor_wheel_url'];expected=pins['harbor_wheel_sha256']
    assert url.startswith('https://files.pythonhosted.org/packages/') and url.endswith('/harbor-0.6.6-py3-none-any.whl')
    assert expected=='30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652'
    directory=ROOT/'inputs-private';directory.mkdir(mode=0o700,exist_ok=True)
    archive=directory/'harbor-0.6.6-py3-none-any.whl'
    if not archive.exists():
        pending=directory/'wheel-download.partial';assert not pending.exists()
        with urllib.request.urlopen(url,timeout=60) as source,pending.open('xb') as dest:
            total=0
            while chunk:=source.read(1024*1024):
                total+=len(chunk);assert total<=LIMIT;dest.write(chunk)
        assert sha(pending)==expected;pending.rename(archive)
    assert sha(archive)==expected and archive.stat().st_size<=LIMIT
    source=directory/'source';source.mkdir(exist_ok=True)
    files=[];total=0
    with zipfile.ZipFile(archive) as wheel:
        assert len(wheel.infolist())<2000 and len(wheel.namelist())==len(set(wheel.namelist()))
        for entry in wheel.infolist():
            name=PurePosixPath(entry.filename);assert not name.is_absolute() and '..' not in name.parts
            if entry.is_dir():continue
            if not (entry.filename.endswith('.py') or entry.filename.endswith('.dist-info/METADATA') or '/licenses/' in entry.filename):continue
            assert entry.file_size<1024**2 and (entry.external_attr>>16)&0o170000!=0o120000
            total+=entry.file_size;assert total<=8*1024**2
            raw=wheel.read(entry);raw.decode('utf8')
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():assert dest.read_bytes()==raw
            else:dest.write_bytes(raw)
            files.append(dict(path=entry.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    metadata=next(r for r in files if r['path'].endswith('.dist-info/METADATA'))
    text=(source/metadata['path']).read_text();assert '\nName: harbor\n' in text and '\nVersion: 0.6.6\n' in text
    result=dict(issue=41,version='0.6.6',created_utc=datetime.now(timezone.utc).isoformat(),source_url=url,
        source_pins_sha256=sha(pin_path),wheel_sha256=expected,wheel_bytes=archive.stat().st_size,selected_source_bytes=total,
        source_files=files,package_installed=False,package_executed=False,model_calls=0,remote_jobs=0,
        retention='Keep task-owned wheel/source until reviewed derived evidence and source availability are verified, then clean duplicates.')
    (ROOT/'package-acquisition.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(version='0.6.6',wheel_bytes=archive.stat().st_size,source_files=len(files),source_bytes=total,package_executed=False)))


if __name__=='__main__':main()
