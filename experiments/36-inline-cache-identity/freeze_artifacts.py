"""Deterministic public-eligible task/source bundles; no upload."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(name,sources):
    path=ROOT/'inputs-private'/name
    assert not path.exists(), 'Never overwrite prepared evidence'
    rows=[]
    with path.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',filename='',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
        for name,source in sorted(sources.items()):
            assert source.is_file() and not source.is_symlink() and source.stat().st_size<1024**2
            raw=source.read_bytes();raw.decode('utf-8')
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=source.stat().st_mode&0o777
            import io
            tar.addfile(member,io.BytesIO(raw))
            rows.append(dict(path=name,bytes=len(raw),mode=member.mode,sha256=hashlib.sha256(raw).hexdigest()))
    with tarfile.open(path) as tar:
        members=tar.getmembers();assert len(members)==len(rows)
        expected={r['path']:r for r in rows}
        for member in members:
            row=expected[member.name]
            assert member.isfile() and member.size==row['bytes'] and member.mode==row['mode']
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==row['sha256']
    return dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=sha(path),members=rows)


def main():
    comparison=json.loads((ROOT/'metadata-comparison.json').read_text())
    prepared=next(r for r in comparison['variants'] if r['variant']=='candidate')
    assert prepared['state']=='prepared' and prepared['native_result']['tasks_rewritten']==12
    tasks=ROOT/'inputs-private/candidate/tasks'
    sources={}
    for name,spec in prepared['inventory'].items():
        path=tasks/name
        assert sha(path)==spec['sha256'] and path.stat().st_size==spec['bytes']
        assert path.stat().st_mode&0o777==spec['mode']
        sources['outputs/OHIF__Viewers/'+name]=path
    candidate=bundle('candidate-tasks.tar.gz',sources)
    baseline=ROOT.parents[3]/'experiments/28-catalogued-fields'
    prior=json.loads((baseline/'history-wide/archives/OHIF__Viewers-manifest.json').read_text())
    ledger=json.loads((ROOT.parents[2]/'33/experiments/33-unattended-validation/task-execution-ledger.json').read_text())
    refs={t[k] for t in ledger['tasks'] if t['repo']=='OHIF/Viewers' for k in ('base_commit','head_commit')}
    wanted=['source-notices/OHIF__Viewers--LICENSE']+[
        'source-notices/history/OHIF__Viewers/'+ref+'--LICENSE' for ref in sorted(refs)]
    sources={}
    for name in wanted:
        row=next(r for r in prior['files'] if r['path']==name)
        if '/history/' in name:
            path=baseline/'history-wide/source-notices'/name.removeprefix('source-notices/history/')
        else:path=baseline/'preflight/licenses'/name.removeprefix('source-notices/')
        assert sha(path)==row['sha256'];sources[name]=path
    upstream=ROOT.parents[2]/'35/experiments/35-durable-runtime-artifacts/private/cold-snapshot/source-notices/Repo2RLEnv-LICENSE'
    assert sha(upstream)=='c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'
    sources['source-notices/Repo2RLEnv-LICENSE']=upstream
    current=json.loads((ROOT/'current-upstream-source.json').read_text())
    for row in current['files']:
        path=ROOT/'inputs-private/current-upstream'/row['path']
        assert sha(path)==row['sha256'];sources['upstream-current/'+row['path']]=path
    source_bundle=bundle('source-evidence.tar.gz',sources)
    report=dict(candidate=candidate,source=source_bundle,model_calls=0,docker_commands=0,
        third_party_terms='Original OHIF and Repo2RLEnv source notices retained; no relicensing',
        scope='Experimental metadata candidate, not runtime-validated exports')
    (ROOT/'artifact-inputs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(candidate_files=len(candidate['members']),source_files=len(source_bundle['members']),
        bundle_bytes=candidate['bytes']+source_bundle['bytes'],submitted=False)))


if __name__=='__main__':main()
