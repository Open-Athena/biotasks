"""Resume the frozen cohort once its two existing dependencies are complete.

This experiment-only handoff does not submit jobs itself or retry failed stages.
The normal cohort controller retains all admission, budget and identity checks.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'inputs-private/run-002'
PINS = {
    ROOT / 'manifest-002.json': '106c3212096f39b3eac8932b178ebce9cae436479527bf671d21b755314488a7',
    WORK / 'manifest-plan.json': '7cf4fa8dd7f2e8cccfb55729990623c8ecadfd5bd4c178a22f3434cb5fa59ba8',
}
STAGES = ['candidate_verified', 'submission_recorded', 'remote_terminal', 'archive_readback_verified', 'publication_resolved', 'cleanup_terminal', 'cleanup_verified']


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def process_alive(record):
    assert len(record) == 1
    p = record[0]
    try:
        fields = Path(f'/proc/{p["pid"]}/stat').read_text().split()
        return fields[21] == p['start_ticks'] and fields[2] != 'Z'
    except FileNotFoundError:
        return False


def complete(directory):
    journal = read(directory / 'journal.json')
    if [s['stage'] for s in journal['stages']] != STAGES or journal.get('intent'):
        return False
    assert read(directory / 'cleanup-proof.json')['verified_empty'] is True
    retained = read(directory / 'readback.json')
    assert retained['durable_readback_verified'] is True and retained['verified_stopped'] is True
    return True


def assess():
    for path, expected in PINS.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Frozen handoff input changed'
    generation = WORK / 'dendropy/runs/generation'
    running = process_alive(read(ROOT / 'controller-process-003.json'))
    if running:
        return 'waiting_for_existing_dendropy_controller'
    assert complete(generation), 'DendroPy stopped without verified completion; review required'
    cleanup = WORK / 'nibabel-handoff/validation/runs/task-810bdc60ecd7'
    if not complete(cleanup):
        assert process_alive(read(ROOT / 'cleanup-waiter-process.json')), 'Cleanup waiter stopped; review required'
        waiter = read(ROOT / 'cleanup-wait-state.json')
        assert waiter['original_control_run_id'] == 'biotasks-val-issue67b-nibabel-6cca5227b8e1'
        assert waiter['state'] == 'waiting_for_original_worker_headroom', 'Unexpected cleanup state; review required'
        return 'waiting_for_existing_nibabel_cleanup'
    return 'ready_for_original_cohort_resume'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    if not args.watch:
        print(json.dumps({'state': assess(), 'read_only': True}), flush=True)
        return
    with (ROOT / 'inputs-private/resume-handoff.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handoff = ROOT / 'inputs-private/resume-handoff-started.json'
        assert not handoff.exists(), 'Original handoff already attempted; review before restarting'
        save(ROOT / 'controller-process-004.json', [{'pid': os.getpid(), 'start_ticks': Path('/proc/self/stat').read_text().split()[21]}])
        previous = None
        while True:
            state = assess()
            value = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'state': state, 'new_manifest': False, 'generation_retry': False, 'native_repair': False}
            save(ROOT / 'inputs-private/resume-handoff-state.json', value)
            if state != previous:
                print(json.dumps(value), flush=True)
                previous = state
            if state == 'ready_for_original_cohort_resume':
                # One handoff, with the same PID, into the original controller.
                # Its frozen plans/receipts prevent completed generation or
                # controls from being repeated. An unfamiliar failure exits.
                with handoff.open('x') as receipt:
                    receipt.write(json.dumps(value, indent=2) + '\n')
                os.execv('/bin/bash', ['bash', str(ROOT / 'launch.sh'), 'recover'])
            time.sleep(300)


if __name__ == '__main__':
    main()
