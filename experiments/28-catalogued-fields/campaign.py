"""Discrete serial submit/observe/harvest operations; never regenerate a result."""

import argparse
from contextlib import ExitStack
import dataclasses
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
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


def run_id(row):
    return 'biotasks28-' + row['slug'].lower().replace('__', '-') + '-001'


def finished_records(state):
    return [json.loads(p.read_text()) for p in sorted(state.glob('*-terminal.json'))]


def submit_next(args):
    cohort = json.loads((ROOT / 'cohort.json').read_text())
    pins = json.loads((ROOT / 'pins.json').read_text())
    assert len(cohort) * pins['job_timeout_seconds'] * 4 / 3600 <= pins['aggregate_allocated_cpu_hour_ceiling']
    checkpoint = json.loads((ROOT / 'input-checkpoint.json').read_text())
    for relative, expected in checkpoint['payload_files'].items():
        with (ROOT / relative).open('rb') as handle:
            assert hashlib.file_digest(handle, 'sha256').hexdigest() == expected['sha256'], relative
    for relative in ['submit.py', 'cohort.json']:
        path = ROOT / relative
        repository_path = path.relative_to(ROOT.parents[1])
        original = subprocess.check_output(['git', 'show', checkpoint['checkpoint_commit'] + ':' + str(repository_path)])
        assert path.read_bytes() == original, 'Uncheckpointed submission/cohort input: ' + relative
    actual = Decimal('0')
    for row in cohort:
        run = run_id(row)
        receipt = args.state_dir / (run + '-receipt.json')
        terminal = args.state_dir / (run + '-terminal.json')
        if terminal.exists():
            value = json.loads(terminal.read_text())
            assert value.get('readback_verified') and value.get('supervisor', {}).get('cleanup', {}).get('verified_empty')
            billing = value.get('billing')
            assert billing and billing['cost_complete'], 'Resolve missing actual billing before continuing'
            actual += Decimal(billing['actual_cost_usd'])
            continue
        if receipt.exists():
            print(json.dumps({'run_id': run, 'action': 'observe_existing_handle'}))
            return
        assert actual < Decimal(str(pins['aggregate_actual_model_stop_threshold_usd'])), 'Aggregate actual-cost stop'
        subprocess.run([sys.executable, str(ROOT / 'submit.py'), '--config', str(args.config),
                        '--receipt', str(receipt), '--run-id', run, '--phase', 'generate',
                        '--input', row['slug'] + '.json'], check=True)
        return
    print('All ten submitted jobs have archived readback, billing and owned cleanup records.')


def download(archive, destination, gcloud, *, max_expanded_bytes=2 * 1024**3):
    # Streaming extraction; never load an archive or tar member into memory.
    assert archive['state'] == 'uploaded' and archive['size_bytes'] < 1024**3
    path = destination / 'outputs.tar.zst'
    if not path.exists():
        partial = path.with_suffix('.partial')
        subprocess.run([gcloud, 'storage', 'cp', '--quiet', archive['uri'], str(partial)],
                       capture_output=True, check=True, timeout=240)
        partial.replace(path)
    assert path.stat().st_size == archive['size_bytes']
    with path.open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == archive['sha256']
    extracted = 0
    with path.open('rb') as compressed, zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
        with tarfile.open(fileobj=stream, mode='r|') as bundle:
            for member in bundle:
                if member.isdir():
                    continue
                assert member.isfile() and Path(member.name).name == member.name
                extracted += member.size
                assert member.size < 1024**3 and extracted < max_expanded_bytes
                with bundle.extractfile(member) as source, (destination / member.name).open('wb') as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
    return extracted


def billing_from_archive(path, *, max_uncompressed_bytes=2 * 1024**3):
    if not path.exists():
        return None
    billing = None
    events = []
    uncompressed = 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            uncompressed += member.size
            assert uncompressed < max_uncompressed_bytes
            if member.name == 'native-observations/billing.json':
                assert member.size < 10000
                billing = json.load(archive.extractfile(member))
            elif member.name == 'native-observations/events.jsonl':
                assert member.size < 10 * 1024**2
                events = [json.loads(line) for line in archive.extractfile(member) if line.strip()]
    if billing is None:
        return None
    # A killed in-flight request can leave the preceding billing snapshot intact.
    # Reconcile dispatched calls against charges, rather than trusting that snapshot.
    dispatched = {event['call'] for event in events if event['event'] == 'model_request'}
    charges = {event['call']: event['actual_cost_usd'] for event in events
               if event['event'] == 'model_charge' and event['actual_cost_usd'] is not None}
    actual = sum((Decimal(value) for value in charges.values()), Decimal('0'))
    billing['observer_snapshot_cost_usd'] = billing['actual_cost_usd']
    billing['actual_cost_usd'] = str(actual)
    billing['dispatched_calls'] = len(dispatched)
    billing['unresolved_calls'] = sorted(dispatched - set(charges))
    billing['cost_complete'] = (billing['cost_complete'] and not billing['unresolved_calls']
                                and actual == Decimal(billing['observer_snapshot_cost_usd']))
    return billing


def observe(args):
    receipt = args.state_dir / (args.run_id + '-receipt.json')
    assert receipt.exists(), 'No submitted handle'
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            job = client.job(JobName.from_string('/exedev/' + args.run_id))
            state = job.status()
            print(json.dumps({'run_id': args.run_id, 'state': state.state.name}), flush=True)
            for line in job.logs(max_lines=12):
                print(line.data, flush=True)
            if not is_job_finished(state.state):
                return
            attempts = [dataclasses.asdict(a) for a in job.task(0).describe().status.attempts]
    target = args.state_dir / (args.run_id + '-terminal.json')
    record = json.loads(target.read_text()) if target.exists() else {
        'run_id': args.run_id, 'state': state.state.name, 'attempts': attempts, 'readback_verified': False}
    record.update(state=state.state.name, attempts=attempts)
    save(target, record)
    if args.action != 'harvest' or record['readback_verified']:
        print(json.dumps({'terminal_record': str(target), 'readback_verified': record['readback_verified']}))
        return
    archive = attempts[-1]['output_archive'] if attempts else None
    assert archive and archive['state'] == 'uploaded', 'Wait on the same handle for output upload'
    lightweight = archive['size_bytes'] < 1024**2
    with ExitStack() as stack:
        if not lightweight:
            lock = stack.enter_context(open('/tmp/exe-codex-local-heavy.lock', 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
        assert mem >= 2.5 * 1024**3 and mem - 256 * 1024**2 >= 2 * 1024**3
        if not lightweight:
            assert os.getloadavg()[0] < 1.5
        os.nice(10)
        started = time.time()
        destination = args.state_dir / (args.run_id + '-results')
        destination.mkdir(exist_ok=True)
        record['extracted_bytes'] = download(archive, destination, args.gcloud,
            max_expanded_bytes=8 * 1024**2 if lightweight else 2 * 1024**3)
        report = destination / 'supervisor-result.json'
        if report.exists():
            record['supervisor'] = json.loads(report.read_text())
        record['billing'] = billing_from_archive(destination / 'phase-artifacts.tar.gz',
            max_uncompressed_bytes=16 * 1024**2 if lightweight else 2 * 1024**3)
        if record['billing'] is None and not record.get('supervisor', {}).get('phase_started'):
            record['billing'] = {'actual_cost_usd': '0', 'cost_complete': True, 'model_calls': 0,
                                 'reason': 'infrastructure_failed_before_native_start'}
        record['harvest'] = {'started': started, 'finished': time.time(),
                             'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                             'estimate_mib': 256, 'lightweight_metadata': lightweight,
                             'archive_sha256': archive['sha256']}
        record['readback_verified'] = True
        save(target, record)
        print(json.dumps({'readback_verified': True, 'billing': record['billing'],
                          'owned_cleanup': record.get('supervisor', {}).get('cleanup', {}).get('verified_empty')}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['submit-next', 'observe', 'harvest', 'watch'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--run-id')
    parser.add_argument('--gcloud', default='/home/exedev/.local/google-cloud-sdk/bin/gcloud')
    args = parser.parse_args()
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.action == 'submit-next':
        submit_next(args)
    elif args.action == 'watch':
        # Foreground orchestration only; no detached work or model calls here.
        cohort = json.loads((ROOT / 'cohort.json').read_text())
        while True:
            if (args.state_dir / 'HOLD').exists():
                print('HOLD present; no further submissions. Existing remote job remains bounded.', flush=True)
                return
            pending = next((row for row in cohort if not (
                (args.state_dir / (run_id(row) + '-terminal.json')).exists()
                and json.loads((args.state_dir / (run_id(row) + '-terminal.json')).read_text()).get('readback_verified'))), None)
            if pending is None:
                submit_next(args)  # Recheck every cost/cleanup gate before declaring terminal.
                return
            args.run_id = run_id(pending)
            if not (args.state_dir / (args.run_id + '-receipt.json')).exists():
                submit_next(args)
            args.action = 'harvest'
            observe(args)
            terminal = args.state_dir / (args.run_id + '-terminal.json')
            if terminal.exists() and json.loads(terminal.read_text()).get('readback_verified'):
                continue
            time.sleep(180)
    else:
        assert args.run_id
        observe(args)


if __name__ == '__main__':
    main()
