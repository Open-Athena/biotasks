"""Experimental one-step controller with durable intent and evidence gates.

Adapters own remote status, budgets, artifact verification and publication policy.
The journal never treats command exit status as evidence of scientific success.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


STAGES = (
    'candidate_verified', 'submission_recorded', 'remote_terminal',
    'archive_readback_verified', 'public_eligibility_reviewed',
    'hf_readback_verified', 'cleanup_terminal', 'cleanup_verified',
)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def controller_lock(journal):
    """Per-run coordination only; not the shared heavy-work lock."""
    lock = Path(str(journal) + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def verify_bindings(bindings):
    for item in bindings:
        if digest(item['path']) != item['sha256']:
            raise ValueError('Evidence changed: ' + item['path'])


def advance(plan, journal_path, adapter):
    """Advance at most one stage. Unknown effects are recovered, never repeated.

    probe(stage) returns {state: pending|ready|absent, evidence: file bindings}.
    perform(stage) is allowed only after a first authoritative absent observation.
    recover(stage) may continue an idempotent operation or query its fixed handle;
    it must never retry an uncertain submission under a new handle.
    verify(stage, evidence) checks stage-specific semantic gates, not just hashes.
    """
    journal_path = Path(journal_path)
    with controller_lock(journal_path):
        verify_bindings(plan['inputs'])
        if journal_path.exists():
            journal = json.loads(journal_path.read_text())
            if journal['plan_sha256'] != identity(plan):
                raise ValueError('Plan changed; use a separate experiment')
        else:
            journal = dict(plan_sha256=identity(plan), run_id=plan['run_id'], stages=[], events=[])
            atomic_write(journal_path, journal)
        for index, record in enumerate(journal['stages']):
            if record['stage'] != STAGES[index]:
                raise ValueError('Noncontiguous journal stages')
            verify_bindings(record['evidence'])
            adapter.verify(record['stage'], record['evidence'])
        if len(journal['stages']) == len(STAGES):
            return 'complete'
        stage = STAGES[len(journal['stages'])]
        # Observation failure propagates without deleting the intent or advancing.
        observation = adapter.probe(stage)
        if observation['state'] == 'ready':
            evidence = observation['evidence']
            if not evidence:
                raise ValueError('Stage has no durable evidence')
            verify_bindings(evidence)
            adapter.verify(stage, evidence)
            journal['stages'].append(dict(stage=stage, evidence=evidence))
            journal.pop('intent', None)
            journal['events'].append(dict(stage=stage, event='evidence_verified'))
            atomic_write(journal_path, journal)
            return stage
        if observation['state'] == 'pending':
            return 'waiting:' + stage
        if observation['state'] != 'absent':
            raise ValueError('Unknown observation state')
        if journal.get('intent'):
            if journal['intent']['stage'] != stage:
                raise ValueError('Intent stage mismatch')
            adapter.recover(stage)
            return 'recovering:' + stage
        journal['intent'] = dict(stage=stage, run_id=plan['run_id'])
        journal['events'].append(dict(stage=stage, event='intent_persisted'))
        atomic_write(journal_path, journal)
        adapter.perform(stage)
        # A subsequent call must independently inspect durable evidence.
        return 'performed:' + stage
