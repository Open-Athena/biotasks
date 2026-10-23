"""One isolated writer dependency for local package integration checks."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent


def main():
    with urllib.request.urlopen('https://pypi.org/pypi/tomli-w/1.2.0/json',timeout=30) as response:meta=json.loads(response.read(100000))
    wheel=next(x for x in meta['urls'] if x['filename']=='tomli_w-1.2.0-py3-none-any.whl')
    assert wheel['size']<100000
    path=ROOT/'inputs-private'/wheel['filename']
    if not path.exists():
        with urllib.request.urlopen(wheel['url'],timeout=30) as response:data=response.read(100001)
        assert len(data)==wheel['size'] and hashlib.sha256(data).hexdigest()==wheel['digests']['sha256'];path.write_bytes(data)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==wheel['digests']['sha256']
    dest=ROOT/'inputs-private/check-deps'
    with zipfile.ZipFile(path) as z:
        assert sum(i.file_size for i in z.infolist())<100000
        for item in z.infolist():
            p=PurePosixPath(item.filename);assert not p.is_absolute() and '..' not in p.parts
            if item.is_dir():continue
            target=dest/item.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
    report={'package':'tomli-w','version':'1.2.0','wheel':wheel['filename'],'sha256':wheel['digests']['sha256'],'bytes':wheel['size'],'source':wheel['url'],'scope':'Isolated local integration-check dependency; no shared environment or biological runtime changed'}
    (ROOT/'check-dependency.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
