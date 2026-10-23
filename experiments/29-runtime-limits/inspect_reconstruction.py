"""Restore/inspect original bootstrap metadata, without executing any recipe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['restore', 'inspect'])
parser.add_argument('--baseline-root', required=True, type=Path)
parser.add_argument('--matchms-original', type=Path)
args = parser.parse_args()
private = ROOT / 'inputs-private'
private.mkdir(mode=0o700, exist_ok=True)
plan = json.loads((ROOT / 'control-plan.json').read_text())

if args.action == 'restore':
    os.environ.update(json.loads((args.baseline_root / 'archive-client-profile.json').read_text())['environment'])
    cache = private / 'xet-cache'
    os.environ['HF_XET_CACHE'] = str(cache)
    from huggingface_hub import HfApi
    records = []
    try:
        for repo in plan['repositories']:
            slug = repo['slug']
            if slug == 'matchms__matchms':
                assert args.matchms_original is not None
                path = args.matchms_original
                retention = 'Protected original read in place; not copied/uploaded/deleted'
            else:
                path = private / (slug + '-phase.tar.gz')
                receipt = json.loads((args.baseline_root / 'archives' / (slug + '-receipt.json')).read_text())
                assert repo['original_phase']['bytes'] < 10 * 1024**2
                if not path.exists():
                    HfApi(token=False).download_bucket_files(receipt['bucket'], [(receipt['prefix'] + '/' + repo['original_phase']['path'], path)], token=False, raise_on_missing_files=True)
                retention = 'Local active-use copy of verified public original'
            assert path.stat().st_size == repo['original_phase']['bytes']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == repo['original_phase']['sha256']
            with tarfile.open(path, 'r:gz') as archive:
                for m in archive:
                    if not m.isfile() or not (m.name.startswith('bootstrap/') and m.name.endswith('bootstrap.json')):
                        continue
                    raw = archive.extractfile(m).read()
                    expected = next(r for r in repo['reconstruction_records'] if r['path'] == m.name)
                    assert hashlib.sha256(raw).hexdigest() == expected['sha256']
                    target = private / (slug + '-bootstrap.json')
                    target.write_bytes(raw)
                    target.chmod(0o600)
                    records.append({'slug': slug, 'phase_sha256': repo['original_phase']['sha256'], 'member': m.name,
                                    'member_sha256': expected['sha256'], 'local_metadata': str(target.relative_to(ROOT)), 'retention': retention})
        (ROOT / 'reconstruction-readback.json').write_text(json.dumps(records, indent=2)+'\n')
        print(json.dumps({'original_bootstrap_records_verified': len(records)}))
    finally:
        if cache.exists():
            shutil.rmtree(cache)
else:
    results = []
    for row in json.loads((ROOT / 'reconstruction-readback.json').read_text()):
        raw = (ROOT / row['local_metadata']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['member_sha256']
        boot = json.loads(raw)
        checks = []
        dockerfile = boot.get('dockerfile_reconstruction', '')
        for n, line in enumerate(dockerfile.splitlines(), 1):
            if line.startswith('RUN '):
                command = line[4:]
                r = subprocess.run(['/bin/bash', '-n', '-c', command], text=True, capture_output=True, timeout=3)
                checks.append({'line': n, 'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
                               'syntax_exit': r.returncode, 'diagnostic': r.stderr.strip()})
        results.append({'slug': row['slug'], 'metadata_sha256': row['member_sha256'],
                        'ref': boot.get('ref'), 'original_image_digest': boot.get('image_digest'),
                        'smoke_passed': boot.get('smoke_passed'), 'verify_passed': boot.get('verify_passed'),
                        'saved_rebuild_command_count': len(boot.get('rebuild_cmds', [])),
                        'saved_dockerfile_sha256': hashlib.sha256(dockerfile.encode()).hexdigest(),
                        'dockerfile_present': bool(dockerfile), 'run_syntax_checks': checks,
                        'syntax_error_count': sum(x['syntax_exit'] != 0 for x in checks),
                        'scope': 'Shell syntax only, no build, dependency install or task execution; syntax pass is not image reproducibility'})
    (ROOT / 'reconstruction-findings.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps([{'slug':r['slug'], 'syntax_errors':r['syntax_error_count'], 'run_count':len(r['run_syntax_checks'])} for r in results]))
