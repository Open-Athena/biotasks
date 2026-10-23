"""Verify the ownership-gated MACS image cleanup output archive."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import zstandard
ROOT=Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    a=json.loads((ROOT/'macs-742-image-cleanup-accounting.json').read_text())
    assert a['state']=='succeeded' and a['attempts']==1 and a['exit_code']==0
    remote=a['output_archive'];assert remote['state']=='uploaded' and remote['size_bytes']<1024*1024
    dest=ROOT/'inputs-private/macs-742-image-cleanup-001';dest.mkdir(parents=True,mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',remote['uri'],str(archive)],capture_output=True,check=True,timeout=90)
    assert archive.stat().st_size==remote['size_bytes'] and sha(archive)==remote['sha256']
    members=[]
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            path=PurePosixPath(member.name);assert not path.is_absolute() and '..' not in path.parts
            if member.isdir():continue
            assert member.isfile() and member.size<1024*1024
            target=dest/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(member).read();assert len(data)==member.size
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data);target.chmod(0o600)
            members.append({'path':member.name,'bytes':member.size,'sha256':sha(target)})
    result=json.loads((dest/'cleanup-result.json').read_text())
    assert result['owner']=='biotasks31-macs-742-image-001' and result['verified_empty']
    assert result['remaining_images']==[] and result['remaining_containers']==[] and result['tools_removed']
    report={'archive_sha256':remote['sha256'],'members':members,'result':result,'allocated_cpu_hours':a['allocated_cpu_hours'],'model_calls':0}
    (ROOT/'macs-742-image-cleanup-readback-001.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='members'}))
if __name__=='__main__':main()
