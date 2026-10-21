"""Serial orchestration only: native generation/controls are unchanged.

Credentials enter through the environment. Private receipts prevent resubmission;
archives remain private pending publication review. Poll every three minutes.
"""
import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import zstandard
from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT = Path(__file__).resolve().parent


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, default=str) + '\n')
    temporary.replace(path)


def download(archive, destination, gcloud):
    assert archive['state'] == 'uploaded' and archive['size_bytes'] < 50 * 1024**2
    path = destination / 'outputs.tar.zst'
    subprocess.run([gcloud, 'storage', 'cp', archive['uri'], str(path)],
                   capture_output=True, check=True, timeout=120)
    assert path.stat().st_size == archive['size_bytes']
    with path.open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == archive['sha256']
    extracted = 0
    with path.open('rb') as compressed:
        with zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
            with tarfile.open(fileobj=stream, mode='r|') as bundle:
                for member in bundle:
                    if not member.isfile(): continue
                    assert member.size < 20 * 1024**2
                    extracted += member.size
                    assert extracted < 200 * 1024**2
                    assert Path(member.name).name == member.name
                    with (destination / member.name).open('wb') as output:
                        source = bundle.extractfile(member)
                        while chunk := source.read(1024 * 1024): output.write(chunk)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--gcloud', required=True)
    args = parser.parse_args()
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert os.environ.get('GH_TOKEN') and os.environ.get('OPENROUTER_API_KEY')
    cohort = json.loads((ROOT / 'cohort.json').read_text())
    budget = json.loads((ROOT / 'pins.json').read_text())['aggregate_allocated_cpu_hour_ceiling']
    # Each normal attempt is capped at 1.5 hours * four CPUs; 18 total.
    assert len(cohort) * 6 < budget
    for row in cohort:
        slug = row['repo'].replace('/', '__')
        run = 'biotasks27-' + row['repo'].split('/')[-1] + '-001'
        receipt = args.state_dir / (run + '-receipt.json')
        terminal = args.state_dir / (run + '-terminal.json')
        if not receipt.exists():
            subprocess.run([sys.executable, str(ROOT / 'submit.py'), '--config', str(args.config),
                            '--receipt', str(receipt), '--run-id', run, '--phase', 'generate',
                            '--input', row['configuration']], check=True)
        # Always inspect the original deterministic job handle, never resubmit.
        with connect_controller(config_file=args.config) as endpoint:
            with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
                job = client.job(JobName.from_string('/exedev/' + run))
                while True:
                    state = job.status()
                    print(json.dumps({'run_id': run, 'state': state.state.name}), flush=True)
                    if is_job_finished(state.state): break
                    time.sleep(180)
                attempts = [dataclasses.asdict(a) for a in job.task(0).describe().status.attempts]
                record = {'run_id': run, 'state': state.state.name,
                          'attempts': attempts, 'readback_verified': False}
                save(terminal, record)
                archive = attempts[-1]['output_archive'] if attempts else None
                if archive and archive['state'] == 'uploaded':
                    destination = args.state_dir / (run + '-results')
                    destination.mkdir(exist_ok=True)
                    download(archive, destination, args.gcloud)
                    record['readback_verified'] = True
                    report = destination / 'supervisor-result.json'
                    if report.exists():
                        record['supervisor'] = json.loads(report.read_text())
                    save(terminal, record)
                print(json.dumps({'run_id': run, 'terminal': True,
                                  'readback_verified': record['readback_verified']}), flush=True)
                # A missing archive or unverified cleanup requires a read-only
                # diagnosis before consuming more capacity. No automatic repair.
                assert record['readback_verified'], 'Terminal evidence unavailable'
                report = record.get('supervisor', {})
                assert report.get('cleanup', {}).get('verified_empty'), 'Cleanup not verified'
    print('CAMPAIGN_TERMINAL all three repository jobs archived and cleanup verified', flush=True)


if __name__ == '__main__': main()
