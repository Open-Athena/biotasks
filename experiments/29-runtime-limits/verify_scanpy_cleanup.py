"""Hash-verified readback of cleanup-only evidence for the exact original label."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
import zstandard
ROOT=Path(__file__).resolve().parent


def main():
    account=json.loads((ROOT/'scanpy-cleanup-accounting.json').read_text());assert account['state']=='succeeded' and account['attempts']==1
    a=account['output_archive'];assert a['state']=='uploaded' and a['size_bytes']<100000
    dest=ROOT/'inputs-private/scanpy-cleanup-001';dest.mkdir(mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',a['uri'],str(archive)],capture_output=True,check=True,timeout=60)
    assert archive.stat().st_size==a['size_bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==a['sha256']
    data=None
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for m in tar:
            if m.isdir():continue
            assert m.name=='cleanup-result.json' and m.isfile() and m.size<10000 and data is None
            data=tar.extractfile(m).read()
    result=json.loads(data);assert result==json.loads((ROOT/'scanpy-cleanup-result-001.json').read_text())
    assert result['owner']=='biotasks29-scanpy-reconstruct-001' and result['verified_empty']
    assert result['remaining_images']==[] and result['remaining_containers']==[] and result['tools_removed']
    (dest/'cleanup-result.json').write_bytes(data)
    receipt={'archive_sha256':a['sha256'],'result_sha256':hashlib.sha256(data).hexdigest(),'result_matches_logged_record':True,'verified_empty':True,'model_calls':0}
    (ROOT/'scanpy-cleanup-readback-001.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
