"""Read exact upstream interface blobs; no installation, execution or models."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
REV='27d04ee8203cd5b2f20c3997d13836e5f5b64238'
PATHS=['LICENSE','docs/reference/cli.mdx','src/repo2rlenv/cli.py','src/repo2rlenv/registry/push.py','src/repo2rlenv/hub.py','src/repo2rlenv/registry/integration.py']


def main():
    files=[]
    for name in PATHS:
        request=f'repos/huggingface/Repo2RLEnv/contents/{name}?ref={REV}'
        value=json.loads(subprocess.check_output(['gh','api',request],timeout=60))
        raw=base64.b64decode(value['content'])
        assert len(raw)==value['size'] and len(raw)<1024**2
        git_sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
        assert git_sha==value['sha']
        dest=ROOT/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==raw
        else:dest.write_bytes(raw)
        files.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob=git_sha,url=value['html_url']))
    (ROOT/'source-manifest.json').write_text(json.dumps(dict(revision=REV,source_only=True,model_calls=0,remote_jobs=0,files=files),indent=2)+'\n')
    print(dict(source_files=len(files),model_calls=0,remote_jobs=0))


if __name__=='__main__':main()
