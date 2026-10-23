"""Restore small original MNE phase from the verified public snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[3]/'experiments/28-catalogued-fields/history-wide'
private=ROOT/'inputs-private';private.mkdir(exist_ok=True,mode=0o700)
manifest=json.loads((BASE/'archives/mne-tools__mne-python-manifest.json').read_text())
receipt=json.loads((BASE/'archives/mne-tools__mne-python-receipt.json').read_text())
phase=next(r for r in manifest['files'] if r['path']=='evidence/phase-artifacts.tar.gz')
assert phase['bytes']<1024**2
os.environ.update(json.loads((BASE/'archive-client-profile.json').read_text())['environment'])
cache=private/'mne-xet-cache';os.environ['HF_XET_CACHE']=str(cache)
from huggingface_hub import HfApi
path=private/'mne-original-phase.tar.gz'
try:
    if not path.exists():
        HfApi(token=False).download_bucket_files(receipt['bucket'],[(receipt['prefix']+'/'+phase['path'],path)],token=False,raise_on_missing_files=True)
    assert path.stat().st_size==phase['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==phase['sha256']
    expected={m['path']:m for m in phase['members']};verified=[];total=0
    with tarfile.open(path,'r:gz') as tar:
        for member in tar:
            if member.isdir():continue
            assert member.isfile() and member.size<16*1024**2
            total+=member.size;assert total<32*1024**2
            data=tar.extractfile(member).read();m=expected[member.name]
            assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256']
            verified.append(member.name)
    assert set(verified)==set(expected)
    report={'bucket':receipt['bucket'],'prefix':receipt['prefix'],'archive_sha256':phase['sha256'],
            'archive_bytes':phase['bytes'],'members_verified':len(verified),'uncompressed_bytes':total,
            'local_path':str(path.relative_to(ROOT)),'anonymous_read':True,'model_calls':0,'remote_jobs':0,
            'retention':'Active-use local copy of public immutable snapshot; no source artifacts modified'}
    (ROOT/'mne-input-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:
    if cache.exists():shutil.rmtree(cache)
