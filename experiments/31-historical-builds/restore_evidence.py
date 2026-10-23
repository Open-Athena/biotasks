"""Anonymous, hash-verified restore of one small existing public evidence object."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--baseline-root', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
os.environ.update(json.loads((args.baseline_root / 'archive-client-profile.json').read_text())['environment'])
cache = root / 'inputs-private/xet-cache'
os.environ['HF_XET_CACHE'] = str(cache)
from huggingface_hub import HfApi
slug = 'macs3-project__MACS'
manifest = json.loads((args.baseline_root / 'archives' / (slug + '-manifest.json')).read_text())
receipt = json.loads((args.baseline_root / 'archives' / (slug + '-receipt.json')).read_text())
record = next(r for r in manifest['files'] if r['path'] == 'evidence/phase-artifacts.tar.gz')
assert record['bytes'] < 2 * 1024**2
private = root / 'inputs-private'
private.mkdir(mode=0o700, exist_ok=True)
dest = private / 'original-phase.tar.gz'
try:
    if not dest.exists():
        HfApi(token=False).download_bucket_files(receipt['bucket'], [(receipt['prefix'] + '/' + record['path'], dest)], token=False, raise_on_missing_files=True)
    assert dest.stat().st_size == record['bytes']
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == record['sha256']
    (root / 'restore-receipt.json').write_text(json.dumps({'bucket': receipt['bucket'], 'prefix': receipt['prefix'], 'object': record['path'], 'sha256': record['sha256'], 'bytes': record['bytes'], 'anonymous_readback_verified': True}, indent=2)+'\n')
    print(json.dumps({'bytes': record['bytes'], 'sha256_verified': True}))
finally:
    if cache.exists():
        shutil.rmtree(cache)
