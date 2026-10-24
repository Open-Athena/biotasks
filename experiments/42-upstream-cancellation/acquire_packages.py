"""Bind inspected tag source to published wheel; read the old wheel as data."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import zipfile

ROOT=Path(__file__).resolve().parent


def digest(raw):return hashlib.sha256(raw).hexdigest()


def main():
    assert not (ROOT/'package-source-parity.json').exists()
    baseline=ROOT.parents[2]/'41/experiments/41-verifier-cancellation/inputs-private/payloads/harbor_timeout/harbor-0.6.6-py3-none-any.whl'
    assert digest(baseline.read_bytes())=='30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652'
    paths=['harbor/trial/trial.py','harbor/verifier/verifier.py','harbor/environments/docker/docker.py','harbor/utils/scripts.py']
    old=[]
    with zipfile.ZipFile(baseline) as archive:
        for name in paths:
            raw=archive.read(name);raw.decode('utf-8')
            dest=ROOT/'inputs-private/baseline'/name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(raw)
            old.append(dict(path=name,bytes=len(raw),sha256=digest(raw)))
    metadata=json.loads((ROOT/'package-release-metadata.json').read_text())
    wheels=[r for r in metadata['release_files'] if r['filename'].endswith('.whl')];assert len(wheels)==1
    spec=wheels[0];wheel=ROOT/'inputs-private'/spec['filename'];assert not wheel.exists()
    with urlopen(spec['url'],timeout=60) as response:raw=response.read(8*1024**2+1)
    assert len(raw)<=8*1024**2 and digest(raw)==spec['digests']['sha256'];wheel.write_bytes(raw)
    sources=json.loads((ROOT/'source-acquisition.json').read_text())['records'][0]['files']+json.loads((ROOT/'source-followup.json').read_text())['records'][0]['files']
    compared=[]
    with zipfile.ZipFile(wheel) as archive:
        for row in sources:
            if not row['path'].startswith('src/harbor/'):continue
            name=row['path'].removeprefix('src/');value=archive.read(name)
            assert digest(value)==row['sha256'],name
            compared.append(dict(wheel_path=name,tag_path=row['path'],sha256=digest(value),bytes=len(value)))
    record=dict(issue=42,source_only=True,upstream_executed=False,baseline=dict(version='0.6.6',wheel_sha256=digest(baseline.read_bytes()),files=old,source_issue=41,source_commit='b5533ced'),
        published=dict(version='0.24.0',filename=wheel.name,url=spec['url'],wheel_sha256=digest(raw),bytes=len(raw),tag_runtime_files_verified=compared),model_calls=0)
    (ROOT/'package-source-parity.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(baseline_files=len(old),published_runtime_files_verified=len(compared),installed=False,executed=False)))


if __name__=='__main__':main()
