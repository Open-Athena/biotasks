"""Anonymous source-only readback of previously published, bounded evidence."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil

from common import sha,write

ROOT=Path(__file__).resolve().parent
BUCKET='open-athena/biotasks'


def main():
    tree=ROOT.parents[2];baseline=ROOT.parents[3]/'experiments/28-catalogued-fields/history-wide/archives'
    groups=[('original',baseline/'scverse__scanpy-manifest.json',baseline/'scverse__scanpy-receipt.json',[
        ('evidence/phase-artifacts.tar.gz','original-phase.tar.gz')]),
        ('followup',tree/'33/experiments/33-unattended-validation/followup-evidence-manifest.json',tree/'33/experiments/33-unattended-validation/followup-evidence-receipt.json',[
        ('evidence/29/scanpy-recorded.tar.zst','recorded.tar.zst'),('evidence/29/scanpy-controls.tar.zst','controls.tar.zst'),('evidence/29/scanpy-recorded-cleanup.tar.zst','cleanup.tar.zst')]),
        ('native',tree/'38/experiments/38-manifest-validation/runs/scverse__scanpy/manifest.json',tree/'38/experiments/38-manifest-validation/runs/scverse__scanpy/hf-receipt.json',[
        ('evidence/runtime.tar.zst','native-runtime.tar.zst'),('source/native-tasks.tar.gz','native-tasks.tar.gz'),('source/notices.tar.gz','notices.tar.gz')])]
    directory=ROOT/'inputs-private/acquired';directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    profile=json.loads((ROOT/'archive-client-profile.json').read_text());os.environ.update(profile['environment'])
    cache=directory/'transfer-cache';os.environ['HF_XET_CACHE']=str(cache)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    disable_progress_bars();api=HfApi(token=False);records=[]
    try:
        for kind,mp,rp,wanted in groups:
            manifest=json.loads(mp.read_text());receipt=json.loads(rp.read_text())
            assert receipt['bucket']==BUCKET and receipt['anonymous_download_verified'] and receipt['manifest_sha256']==sha(mp)
            prefix=receipt['prefix'];assert prefix.endswith('/'+sha(mp))
            dest=directory/(kind+'-manifest.json')
            api.download_bucket_files(BUCKET,[(prefix+'/manifest.json',dest)],token=False,raise_on_missing_files=True)
            assert sha(dest)==sha(mp)
            records.append(dict(path=str(dest.relative_to(ROOT)),remote=prefix+'/manifest.json',bytes=dest.stat().st_size,sha256=sha(dest),kind='manifest'))
            for name,local in wanted:
                spec=next(f for f in manifest['files'] if f['path']==name);assert spec['bytes']<1024**2
                dest=directory/local
                api.download_bucket_files(BUCKET,[(prefix+'/'+name,dest)],token=False,raise_on_missing_files=True)
                assert dest.stat().st_size==spec['bytes'] and sha(dest)==spec['sha256']
                records.append(dict(path=str(dest.relative_to(ROOT)),remote=prefix+'/'+name,bytes=spec['bytes'],sha256=spec['sha256'],kind='original_evidence'))
    finally:
        if cache.exists():shutil.rmtree(cache)
    value=dict(issue=40,created_utc=datetime.now(timezone.utc).isoformat(),bucket=BUCKET,anonymous_download_verified=True,
        files=records,transfer_cache_removed=True,total_bytes=sum(r['bytes'] for r in records),model_calls=0,remote_jobs=0)
    write(ROOT/'acquisition.json',value);print(json.dumps(dict(objects=len(records),bytes=value['total_bytes'],anonymous_download_verified=True,model_calls=0,remote_jobs=0)))


if __name__=='__main__':main()
