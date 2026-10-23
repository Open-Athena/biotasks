"""Bounded pinned-source acquisition, checked against Git tree blob identities."""
import hashlib,json,subprocess,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
REV='27d04ee8203cd5b2f20c3997d13836e5f5b64238'


def main():
    tree=json.loads((ROOT/'inputs-private/upstream-tree.json').read_text());assert not tree['truncated']
    files={row['path']:row for row in tree['tree'] if row['type']=='blob' and (row['path'].startswith('src/repo2rlenv/') or row['path'] in ('pyproject.toml','LICENSE'))}
    assert sum(row['size'] for row in files.values())<5*1024**2
    archive=ROOT/'inputs-private/upstream-package.tar.gz'
    if not archive.exists():
        with archive.open('xb') as out:
            process=subprocess.Popen(['gh','api',f'repos/huggingface/Repo2RLEnv/tarball/{REV}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                size=0
                while data:=process.stdout.read(65536):
                    size+=len(data);assert size<20*1024**2;out.write(data)
                assert process.wait(timeout=60)==0
            except BaseException:
                process.kill();process.wait();archive.unlink();raise
    dest=ROOT/'inputs-private/upstream-package'
    records=[];total=0
    with tarfile.open(archive,mode='r|gz') as tar:
        for member in tar:
            total+=member.size;assert total<100*1024**2
            parts=PurePosixPath(member.name).parts
            assert parts and '..' not in parts and not member.name.startswith('/')
            relative='/'.join(parts[1:])
            if relative not in files:continue
            assert member.isfile() and member.size==files[relative]['size']
            data=tar.extractfile(member).read()
            assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==files[relative]['sha']
            target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data)
            records.append({'path':relative,'bytes':len(data),'git_blob':files[relative]['sha'],'sha256':hashlib.sha256(data).hexdigest()})
    assert len(records)==len(files)
    with archive.open('rb') as f:archive_sha=hashlib.file_digest(f,'sha256').hexdigest()
    report={'revision':REV,'source_files':len(records),'source_bytes':sum(r['bytes'] for r in records),'archive_bytes':archive.stat().st_size,'archive_sha256':archive_sha,'files':records,'package_executed':False}
    (ROOT/'package-acquisition.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='files'}))


if __name__=='__main__':main()
