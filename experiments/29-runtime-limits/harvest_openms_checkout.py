"""Verify bounded acquisition archives; no model call or checkout rerun."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zstandard
ROOT=Path(__file__).resolve().parent
REF='5edf83948816aee51225949dd0e613bd40f69c47'

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    account=json.loads((ROOT/'openms-checkout-accounting.json').read_text())
    assert account['state'] in ('succeeded','failed') and account['attempts']==1
    a=account['output_archive'];assert a['state']=='uploaded' and a['size_bytes']<16*1024**2
    dest=ROOT/'inputs-private/openms-checkout-001';dest.mkdir(mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',a['uri'],str(archive)],capture_output=True,check=True,timeout=90)
    assert archive.stat().st_size==a['size_bytes'] and sha(archive)==a['sha256']
    members=[];total=0
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for m in tar:
            path=PurePosixPath(m.name);assert not path.is_absolute() and '..' not in path.parts
            if m.isdir():continue
            assert m.isfile() and m.size<16*1024**2
            total+=m.size;assert total<64*1024**2
            target=dest/m.name;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(m).read()
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data);target.chmod(0o600)
            members.append({'path':m.name,'bytes':len(data),'sha256':sha(target)})
    report=json.loads((dest/'openms-checkout-result.json').read_text())
    assert report['run_id']=='biotasks29-openms-checkout-001' and report['model_calls']==0
    for name,digest in report['output_sha256'].items():assert sha(dest/name)==digest
    (ROOT/'openms-checkout-result-001.json').write_text(json.dumps(report,indent=2)+'\n')
    rows=[]
    for seconds in (60,300):
        p=dest/str(seconds)/'checkout-result.json'
        if not p.exists():
            rows.append({'checkout_seconds':seconds,'result_present':False,'checkout_completed':False});continue
        d=json.loads(p.read_text())
        assert d['repo']=='OpenMS/OpenMS' and d['ref']==REF and d['checkout_seconds']==seconds
        assert d['model_calls']==0 and d['bootstrap_started'] is False
        source=ROOT/('upstream/bootstrap/runner.py' if seconds==60 else 'candidate-checkout/runner.py')
        assert d['runner_sha256']==sha(source)
        for number,call in enumerate(d['calls'],1):
            for stream in ('stdout','stderr'):
                if stream+'_sha256' in call:assert sha(p.parent/f'git-{number:02d}-{stream}.txt')==call[stream+'_sha256']
        checkouts=[c for c in d['calls'] if len(c['args'])>=4 and c['args'][3]=='checkout']
        assert len(checkouts)<=1
        if checkouts:assert checkouts[0]['timeout_seconds']==seconds and checkouts[0]['args'][-1]==REF
        if d['checkout_completed']:assert d['checked_out_ref']==REF and d['tracked_status']==''
        rows.append({'checkout_seconds':seconds,'result_present':True,'checkout_completed':d['checkout_completed'],
                     'git_version':d['git_version'],'source_sha256':d['runner_sha256'],'error_type':d.get('error_type'),'error':d.get('error'),
                     'checkout_call':checkouts[0] if checkouts else None,'tree':d.get('tree'),'tracked_status':d.get('tracked_status'),
                     'all_acquisition_calls':d['calls'],'acquisition_wall_seconds':d['finished']-d['started']})
    output={'scope':'Acquisition-only readback at frozen OpenMS ref; not bootstrap, PR discovery or task recovery',
            'ref':REF,'arms':rows,'archive_sha256':a['sha256'],'archive_members':members,
            'owned_containers_absent':report.get('owned_containers_absent',False),'tools_removed':report.get('tools_removed',False),
            'cleanup_errors':report.get('cleanup_errors'),'model_calls':0,'allocated_cpu_hours':account['allocated_cpu_hours'],
            'limits':['Baseline first, shared network/host/remote cache effects are not controlled','Pinned controller image but system package indexes and fetched default-branch history can change','Success means checkout only; no environment installation or generated task follows']}
    (ROOT/'openms-checkout-readback-001.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('archive_members','limits')}))

if __name__=='__main__':main()
