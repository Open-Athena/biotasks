"""Verify original terminal archive and preserve unchanged-recipe outcome privately."""
import hashlib,json,subprocess,tarfile
from pathlib import Path,PurePosixPath
import zstandard
ROOT=Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    account=json.loads((ROOT/'scanpy-reconstruction-accounting.json').read_text())
    assert account['state'] in ('failed','succeeded') and account['attempts']==1
    a=account['output_archive'];assert a['state']=='uploaded' and a['size_bytes']<1024**2
    dest=ROOT/'inputs-private/scanpy-reconstruction-001';dest.mkdir(mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',a['uri'],str(archive)],capture_output=True,check=True,timeout=90)
    assert archive.stat().st_size==a['size_bytes'] and sha(archive)==a['sha256']
    members=[];total=0
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            path=PurePosixPath(member.name);assert not path.is_absolute() and '..' not in path.parts
            if member.isdir():continue
            assert member.isfile();total+=member.size;assert total<10*1024**2
            target=dest/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(member).read()
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data);target.chmod(0o600)
            members.append({'path':member.name,'bytes':len(data),'sha256':sha(target)})
    result_path=dest/'scanpy-reconstruction-result.json'
    report=json.loads(result_path.read_text()) if result_path.exists() else None
    if report:
        assert sha(dest/'build.log')==report['build_log_sha256']
        (ROOT/'scanpy-reconstruction-result-001.json').write_text(json.dumps(report,indent=2)+'\n')
    log=(dest/'build.log').read_text()
    receipt={'archive_sha256':a['sha256'],'members':members,'state':account['state'],
             'result_record_missing':report is None,
             'build_log_has_externally_managed_failure':'error: externally-managed-environment' in log,
             'build_log_has_nonzero_exit':"returned a non-zero code: 1" in log,
             'cleanup_verified':bool(report and report.get('owned_containers_absent') and report.get('owned_image_ids_remaining')==[] and report.get('local_context_tools_removed')),
             'model_calls':0,'controls_run':0,'allocated_cpu_hours':account['allocated_cpu_hours']}
    (ROOT/'scanpy-reconstruction-readback-001.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
