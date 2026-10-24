"""Bounded canonical GitHub source snapshot; never install or execute it."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
REPO='harbor-framework/harbor'


def api(path):
    raw=subprocess.check_output(['gh','api','repos/'+REPO+'/'+path],timeout=60)
    assert len(raw)<4*1024**2
    return json.loads(raw)


def main():
    assert not (ROOT/'source-acquisition.json').exists()
    release=api('releases/latest')
    refs={'release':release['tag_name'],'main':'main'}
    records=[]
    for label,ref in refs.items():
        commit=api('commits/'+ref)
        revision=commit['sha'];tree=api('git/trees/'+revision+'?recursive=1')
        assert not tree['truncated']
        candidates=[r for r in tree['tree'] if r['type']=='blob']
        required=['trial/trial.py','verifier/verifier.py','environments/docker/docker.py','utils/scripts.py']
        paths=[]
        for suffix in required:
            matches=[r['path'] for r in candidates if r['path'].endswith('/harbor/'+suffix)]
            assert len(matches)==1,(ref,suffix,matches)
            paths+=matches
        paths+=['pyproject.toml','LICENSE']
        selected_names={'test_docker.py','test_docker_service_ops.py','test_docker_utils.py','test_verifier.py',
            'test_trial_cleanup.py','test_single_step_trial.py','test_trial_verifier_artifact_transfer.py',
            'test_trial_verifier_separate.py','test_resolved_timeouts.py','test_log_streaming.py'}
        tests=[r['path'] for r in candidates if r['path'].startswith('tests/') and Path(r['path']).name in selected_names]
        assert len(tests)<=40
        paths+=tests
        directory=ROOT/'inputs-private'/label;directory.mkdir()
        files=[]
        for name in sorted(set(paths)):
            entry=next(r for r in candidates if r['path']==name)
            assert entry['size']<=512*1024
            raw=subprocess.check_output(['gh','api','repos/'+REPO+'/contents/'+name+'?ref='+revision,'-H','Accept: application/vnd.github.raw+json'],timeout=60)
            assert len(raw)==entry['size']
            raw.decode('utf-8')
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            assert blob==entry['sha']
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            files.append(dict(path=name,bytes=len(raw),git_blob_sha1=blob,sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/'+REPO+'/blob/'+revision+'/'+name))
        record=dict(label=label,ref=ref,commit=revision,commit_date=commit['commit']['committer']['date'],files=files,
            selected_tests=tests,all_test_paths=[r['path'] for r in candidates if r['path'].startswith('tests/')],
            tree_sha=tree['sha'],tree_truncated=False)
        (directory/'provenance.json').write_text(json.dumps(record,indent=2)+'\n');records.append(record)
    value=dict(issue=42,observed_utc=datetime.now(timezone.utc).isoformat(),upstream=REPO,
        latest_release=dict(tag=release['tag_name'],published_at=release['published_at'],url=release['html_url']),
        records=records,source_only=True,upstream_executed=False,model_calls=0,runtime_cpu_hours=0)
    (ROOT/'source-acquisition.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(revisions=[dict(label=r['label'],commit=r['commit'],files=len(r['files'])) for r in records],source_only=True)))


if __name__=='__main__':main()
