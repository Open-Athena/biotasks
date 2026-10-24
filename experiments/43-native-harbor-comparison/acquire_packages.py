"""Read exact wheel source/configuration as data; no installation or imports."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import zipfile
from common import sha,write

ROOT=Path(__file__).resolve().parent


def main():
    assert not (ROOT/'package-acquisition.json').exists()
    source=json.loads((ROOT/'upstream-package-source.json').read_text());candidate=source['published']
    dest=ROOT/'inputs-private'/candidate['filename']
    with urlopen(candidate['url'],timeout=60) as response:raw=response.read(8*1024**2+1)
    assert len(raw)==candidate['bytes'] and hashlib.sha256(raw).hexdigest()==candidate['wheel_sha256'];dest.write_bytes(raw)
    records=[]
    for version,filename,expected in [('0.6.6','harbor-0.6.6-py3-none-any.whl',source['baseline']['wheel_sha256']),('0.24.0',dest.name,candidate['wheel_sha256'])]:
        wheel=ROOT/'inputs-private'/filename;assert sha(wheel)==expected
        files=[]
        with zipfile.ZipFile(wheel) as archive:
            for info in archive.infolist():
                if info.filename.endswith('.py') or info.filename.endswith('/METADATA') or '/licenses/' in info.filename:
                    assert info.file_size<1024**2
                    raw=archive.read(info);raw.decode('utf-8');path=ROOT/'inputs-private/source'/version/info.filename
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                    files.append(dict(path=info.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        records.append(dict(version=version,filename=filename,wheel_sha256=expected,bytes=wheel.stat().st_size,source_files=files))
    write(ROOT/'package-acquisition.json',dict(issue=43,packages=records,installed_or_executed=False,model_calls=0))
    print(json.dumps(dict(packages=[dict(version=r['version'],source_files=len(r['source_files'])) for r in records],source_only=True)))


if __name__=='__main__':main()
