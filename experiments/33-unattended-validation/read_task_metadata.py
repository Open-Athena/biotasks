"""Read exact exported metadata and build identities from retained evidence."""
import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile
import tomllib

ROOT=Path(__file__).resolve().parent
# Invoke with explicit roots; no assumptions about checkout nesting.

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run(baseline, matchms_originals):
    profile=json.loads((ROOT/'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    ledger=json.loads((ROOT/'task-file-ledger.json').read_text())
    tasks={t['task']:t for t in ledger['tasks']}
    result={};sources=[]
    with tempfile.TemporaryDirectory(prefix='task-metadata-',dir=ROOT/'private') as tmp:
        tmp=Path(tmp);os.environ['HF_XET_CACHE']=str(tmp/'cache')
        from huggingface_hub import HfApi
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars();api=HfApi(token=False)
        for slug in sorted({t['repo'].replace('/','__') for t in tasks.values()}):
            private=slug=='matchms__matchms'
            name='drafts/matchms__matchms-unpublished-private-manifest.json' if private else slug+'-manifest.json'
            manifest=baseline/'archives'/name
            data=json.loads(manifest.read_text())
            prefix='research/28-catalogued-fields/2026-10-23/'+sha(manifest)
            paths={}
            for member in ['evidence/phase-artifacts.tar.gz','evidence/bounded-builds.jsonl']:
                spec=next(f for f in data['files'] if f['path']==member)
                assert spec['bytes']<16*1024**2
                if private:
                    local=matchms_originals/Path(member).name
                else:
                    local=tmp/(slug+'-'+Path(member).name)
                    api.download_bucket_files('open-athena/biotasks',[(prefix+'/'+member,local)],raise_on_missing_files=True,token=False)
                assert local.stat().st_size==spec['bytes'] and sha(local)==spec['sha256']
                paths[member]=local
                sources.append(dict(repo=slug,member=member,sha256=spec['sha256'],bytes=spec['bytes'],
                    source='protected local original' if private else 'verified public HF download'))
            build_rows=[json.loads(line) for line in paths['evidence/bounded-builds.jsonl'].read_text().splitlines() if line]
            with tarfile.open(paths['evidence/phase-artifacts.tar.gz'],'r|gz') as bundle:
                total=0
                for item in bundle:
                    total+=item.size
                    assert total<256*1024**2
                    if not item.name.startswith('outputs/') or not item.name.endswith('/task.toml'):continue
                    assert item.isfile() and item.size<2*1024**2
                    task=Path(item.name).parts[2]
                    assert task in tasks and task not in result
                    raw=bundle.extractfile(item).read()
                    spec=next(f for f in tasks[task]['original_task_files'] if f['path']=='task.toml')
                    assert hashlib.sha256(raw).hexdigest()==spec['sha256']
                    meta=tomllib.loads(raw.decode())['metadata']['repo2env']
                    runtime=meta['pr_runtime']
                    assert meta['repo']==tasks[task]['repo']
                    builds=[r for r in build_rows if Path(r.get('context','')).parent.name==task]
                    result[task]=dict(repo=meta['repo'],base_commit=runtime['base_commit'],
                        head_commit=None,head_status='not present in exported task metadata',
                        bootstrap_image=runtime.get('bootstrap_image'),upstream_content_hash=meta.get('content_hash'),
                        original_runtime_builds=[{k:r.get(k) for k in ['dockerfile_sha256','image','image_id','exit_code']} for r in builds],
                        task_toml_sha256=spec['sha256'])
    assert set(result)==set(tasks)
    report=dict(tasks=result,sources=sources,count=len(result),owned_downloads_removed=not tmp.exists(),
        scope='Actual task metadata bytes and original build records verified; no task execution or source-head inference')
    (ROOT/'task-source-image-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tasks':len(result),'with_runtime_builds':sum(bool(t['original_runtime_builds']) for t in result.values()),'downloads_removed':not tmp.exists()}))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--matchms-originals',type=Path,required=True);a=p.parse_args();run(a.baseline,a.matchms_originals)
