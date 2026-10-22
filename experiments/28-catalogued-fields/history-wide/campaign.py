"""Foreground serial history campaign: original handles, actual billing, cleanup, no repair."""

import argparse
import dataclasses
from decimal import Decimal
import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline_campaign', BASE / 'campaign.py')
baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix('.partial'); temporary.write_text(json.dumps(value, indent=2, default=str) + '\n'); temporary.replace(path)


def billing(path, supervisor, history):
    batches, snapshots = {}, {}
    total_expanded = 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            total_expanded += member.size
            assert total_expanded < 2 * 1024**3
            parts = Path(member.name).parts
            if len(parts) != 3 or parts[0] != 'native-observations':
                continue
            if parts[-1] == 'events.jsonl':
                assert member.size < 16 * 1024**2
                batches[parts[1]] = [json.loads(line) for line in archive.extractfile(member) if line.strip()]
            elif parts[-1] == 'billing.json':
                assert member.size < 10000
                snapshots[parts[1]] = json.load(archive.extractfile(member))
    requests, charges, complete, unresolved = 0, Decimal('0'), True, []
    for name in batches.keys() | snapshots.keys():
        events = batches.get(name, [])
        sent = {e['call'] for e in events if e['event'] == 'model_request'}
        rows = [e for e in events if e['event'] == 'model_charge' and e['actual_cost_usd'] is not None]
        resolved = {e['call']: Decimal(e['actual_cost_usd']) for e in rows}
        assert len(rows) == len(resolved) and set(resolved) <= sent
        assert all(c.is_finite() and c >= 0 for c in resolved.values())
        amount = sum(resolved.values(), Decimal('0'))
        snapshot = snapshots.get(name)
        good = (snapshot and snapshot['cost_complete'] and sent == set(resolved)
            and amount == Decimal(snapshot['actual_cost_usd']))
        complete = bool(complete and good)
        unresolved.extend([{'batch': name, 'call': call} for call in sorted(sent - set(resolved))])
        requests += len(sent); charges += amount
    if not batches and not snapshots:
        # No dispatched request is valid only if native was never entered, or the
        # history orchestrator explicitly started no native batch.
        complete = not supervisor.get('phase_started') or (history is not None and not history['batches'])
    if history and history.get('cost_complete') is False:
        complete = False
    return {'actual_cost_usd': str(charges), 'model_calls': requests,
        'cost_complete': complete, 'unresolved_calls': unresolved,
        'source': 'Original per-batch request/charge events and billing snapshots, no account deltas'}


def run_id(row):
    return 'biotasks28-history-' + row['slug'].lower().replace('__', '-') + '-001'


def remote_record(config, run):
    with connect_controller(config_file=config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            job = client.job(JobName.from_string('/exedev/' + run))
            status = job.status()
            task = job.task(0).describe()
            return {'run_id': run, 'state': status.state.name, 'terminal': is_job_finished(status.state),
                'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'attempts': [dataclasses.asdict(a) for a in task.status.attempts]}


def harvest(args, record):
    assert record['terminal'] and len(record['attempts']) == 1
    archive = record['attempts'][0]['output_archive']
    if not archive or archive['state'] != 'uploaded':
        return None
    target = args.state_dir / (record['run_id'] + '-results'); target.mkdir(exist_ok=True)
    lock = None
    try:
        if archive['size_bytes'] > 32 * 1024**2:
            lock = open('/tmp/exe-codex-local-heavy.lock', 'a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record['extracted_bytes'] = baseline.download(archive, target, args.gcloud, max_expanded_bytes=2 * 1024**3)
    finally:
        if lock:
            lock.close()
    supervisor = read(target / 'supervisor-result.json')
    history = read(target / 'history-batches.json') if (target / 'history-batches.json').exists() else None
    phase = target / 'phase-artifacts.tar.gz'
    if phase.exists():
        costs = billing(phase, supervisor, history)
    else:
        assert not supervisor.get('phase_started')
        costs = {'actual_cost_usd': '0', 'model_calls': 0, 'cost_complete': True,
            'unresolved_calls': [], 'reason': 'Infrastructure ended before native entry'}
    assert costs['cost_complete'], 'Resolve original dispatched charges before any subsequent submission'
    assert supervisor.get('cleanup', {}).get('verified_empty'), 'Verify owned cleanup before another run'
    record.update(readback_verified=True, supervisor=supervisor, billing=costs,
        history_summary={k: v for k, v in history.items() if k not in ['batches', 'backlog_pr_numbers']} if history else None,
        archive_sha256=archive['sha256'])
    save(args.state_dir / (record['run_id'] + '-terminal.json'), record)
    print(json.dumps({'run_id': record['run_id'], 'state': record['state'],
        'readback_verified': True, 'billing': costs, 'owned_cleanup_empty': True}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--gcloud', default='/home/exedev/.local/google-cloud-sdk/bin/gcloud')
    parser.add_argument('--interval', type=int, default=180)
    args = parser.parse_args(); assert args.interval >= 180
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner = {'pid': os.getpid(), 'process_start_ticks': Path('/proc/self/stat').read_text().split(') ', 1)[1].split()[19],
        'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Foreground lightweight serial orchestration; no local native execution or model calls'}
    save(args.state_dir / 'history-watch-owner.json', owner)
    cohort = read(BASE / 'cohort.json')
    try:
        for selected in cohort:
            run = run_id(selected); terminal = args.state_dir / (run + '-terminal.json')
            if terminal.exists():
                r = read(terminal); assert r['readback_verified'] and r['billing']['cost_complete'] and r['supervisor']['cleanup']['verified_empty']
                continue
            if (args.state_dir / 'HOLD').exists():
                print('HOLD: no new submissions; retain existing handles.', flush=True)
                return
            costs = sum((Decimal(read(p)['billing']['actual_cost_usd']) for p in args.state_dir.glob('biotasks28-history-*-terminal.json')), Decimal('0'))
            remaining = Decimal('94.024714') - costs
            assert remaining >= 0
            receipt = args.state_dir / (run + '-receipt.json')
            if not receipt.exists():
                if remaining < Decimal('8.07'):
                    save(args.state_dir / 'history-campaign-budget-stop.json', {
                        'remaining_usd': str(remaining), 'next_repo_unsubmitted': selected['repo'],
                        'reason': 'Cannot reserve initial full-context request under checkpointed route-price bound'})
                    print('Campaign budget boundary: remaining repositories stay unsubmitted with backlog.', flush=True)
                    return
                subprocess.run([sys.executable, str(ROOT / 'submit_history.py'), '--config', str(args.config),
                    '--state-dir', str(args.state_dir), '--slug', selected['slug'], '--remaining-usd', str(remaining)], check=True)
            previous_state = None
            while True:
                try:
                    record = remote_record(args.config, run)
                except Exception as error:
                    print(json.dumps({'run_id': run, 'observation_error': type(error).__name__,
                        'action': 'Keep the same submitted handle; no restart'}), flush=True)
                    time.sleep(args.interval); continue
                save(args.state_dir / (run + '-observation.json'), record)
                if record['state'] != previous_state:
                    print(json.dumps({k: v for k, v in record.items() if k != 'attempts'}), flush=True)
                    previous_state = record['state']
                if record['terminal'] and harvest(args, record):
                    break
                time.sleep(args.interval)
        print('All ten original history handles have terminal readback, complete actual charges and owned cleanup. Scientific assessment, public retention and issue closure remain separate.', flush=True)
    finally:
        owner['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(args.state_dir / 'history-watch-owner.json', owner)


if __name__ == '__main__':
    main()
