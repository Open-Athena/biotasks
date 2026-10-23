"""Verify a terminal MACS comparison archive and summarize both frozen arms."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zstandard

ROOT=Path(__file__).resolve().parent
RUN='biotasks31-macs-native-001'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    account=json.loads((ROOT/'macs-native-accounting.json').read_text())
    assert account['state'] in ('failed','succeeded') and account['attempts']==1
    archive_info=account['output_archive']
    assert archive_info['state']=='uploaded' and archive_info['size_bytes']<64*1024**2
    dest=ROOT/'inputs-private/macs-native-001';dest.mkdir(parents=True,mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',archive_info['uri'],str(archive)],capture_output=True,check=True,timeout=120)
    assert archive.stat().st_size==archive_info['size_bytes'] and sha(archive)==archive_info['sha256']
    members=[];total=0
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            path=PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts and member.size<64*1024**2
            if member.isdir():continue
            assert member.isfile();total+=member.size;assert total<256*1024**2
            target=dest/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256()
            source=tar.extractfile(member)
            if target.exists():
                with target.open('rb') as existing:
                    while chunk:=source.read(1024*1024):
                        assert existing.read(len(chunk))==chunk;digest.update(chunk)
                    assert not existing.read(1)
            else:
                with target.open('wb') as output:
                    while chunk:=source.read(1024*1024):output.write(chunk);digest.update(chunk)
                target.chmod(0o600)
            members.append({'path':member.name,'bytes':member.size,'sha256':digest.hexdigest()})
    report=json.loads((dest/'comparison.json').read_text())
    assert report['run_id']==RUN and report['model_calls']==0 and report['new_capacity'] is False
    assert report['transport']=='original argv'
    assert report['image_id']==json.loads((ROOT/'macs-native-manifest.json').read_text())['image_id']
    for name,digest in report.get('output_sha256',{}).items():assert sha(dest/name)==digest
    manifest=json.loads((ROOT/'macs-native-manifest.json').read_text())
    observations=[]
    for expected,arm in zip(manifest['arms'],report['arms'],strict=False):
        assert arm['name']==expected['name']
        for index,call in enumerate(arm.get('calls',[])):
            stage=call.get('stage')
            if stage:assert call['command_sha256']==expected['stages'][stage]['sha256'] and call['timeout']==600
            for stream in ('stdout','stderr'):
                if stream+'_sha256' in call:
                    assert sha(dest/arm['name']/f'call-{index:02d}-{stream}.txt')==call[stream+'_sha256']
        outcome=dest/arm['name']/'outcome.json'
        actual=json.loads(outcome.read_text()) if outcome.exists() else None
        if actual:assert actual['status']==arm['status'] and actual['reason']==arm['reason']
        observations.append({'name':arm['name'],'state':arm['state'],'status':arm.get('status'),'reason':arm.get('reason'),'calls':len(arm.get('calls',[])),'f2p_count':arm.get('f2p_count'),'p2p_count':arm.get('p2p_count'),'container_removed':arm.get('container_removed',False),'native_outcome_record':bool(actual)})
    receipt={'archive_sha256':archive_info['sha256'],'members':members,'account_state':account['state'],'record_verified':True,'arms':observations,'owned_containers_absent':report.get('owned_containers_absent',False),'tools_removed':report.get('tools_removed',False),'cleanup_errors':report.get('cleanup_errors',[]),'retained_image':report.get('retained_image'),'model_calls':0,'allocated_cpu_hours':account['allocated_cpu_hours']}
    (ROOT/'macs-native-result-001.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'macs-native-readback-001.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='members'}))

if __name__=='__main__':main()
