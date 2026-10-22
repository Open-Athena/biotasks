"""Read-only evidence accounting, retaining upstream and independent outcomes separately."""

import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import tarfile

from campaign import run_id

ROOT = Path(__file__).resolve().parent


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def expand(source, destination):
    destination.mkdir(exist_ok=True)
    total = 0
    with tarfile.open(source, 'r|gz') as archive:
        for member in archive:
            relative = Path(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            if member.isdir():
                continue
            assert member.isfile(), 'Unexpected link or special file in phase evidence'
            total += member.size
            assert member.size < 256 * 1024**2 and total < 2 * 1024**3
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source_file, path.open('wb') as output:
                shutil.copyfileobj(source_file, output, 1024 * 1024)
    return total


def timestamp(value):
    return datetime.datetime.fromisoformat(value.removeprefix('Timestamp(').removesuffix(')'))


def trial_evidence(path, expanded):
    value = load(path)
    details = load(path.parent / 'verifier/reward-details.json')
    reward = ((value.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    reward_file = path.parent / 'verifier/reward.txt'
    written = float(reward_file.read_text().strip()) if reward_file.exists() else None
    detailed = (details or {}).get('reward')
    consistent = None if reward is None else (
        written is not None and detailed is not None and math.isfinite(written)
        and reward == written and math.isclose(detailed, written, rel_tol=0, abs_tol=0.500001e-6))
    log = path.parent / 'trial.log'
    text = log.read_text(errors='replace') if log.exists() else ''
    return {'path': str(path.relative_to(expanded)), 'reward': reward, 'written_reward': written,
        'reward_consistent': consistent,
        'exception': (value.get('exception_info') or {}).get('exception_type'),
        'reward_details': details, 'verifier_started_finished': value.get('verifier'),
        'verifier_timeout_log_lines': [line for line in text.splitlines()
            if 'timed out' in line.lower() or 'retry' in line.lower()]}


def verified_pair(base, oracle, *, files_unchanged):
    return (files_unchanged and base.get('reward') == 0 and oracle.get('reward') == 1
        and base.get('reward_consistent') is True and oracle.get('reward_consistent') is True
        and (base.get('reward_details') or {}).get('parse_status') == 'ok'
        and (oracle.get('reward_details') or {}).get('parse_status') == 'ok'
        and not base.get('exception') and not oracle.get('exception'))


def assess(state, cohort_row):
    run = run_id(cohort_row)
    record = load(state / (run + '-terminal.json'))
    if not record:
        return {'repo': cohort_row['repo'], 'state': 'unstarted_or_active', 'verified_tasks': 0}
    assert record['readback_verified']
    result = state / (run + '-results')
    phase = result / 'phase-artifacts.tar.gz'
    expanded = result / 'expanded'
    if phase.exists() and not (expanded / '.complete').exists():
        expand(phase, expanded)
        (expanded / '.complete').touch()
    observations = expanded / 'native-observations'
    events = [json.loads(line) for line in (observations / 'events.jsonl').read_text().splitlines() if line.strip()] if (observations / 'events.jsonl').exists() else []
    candidates = load(observations / 'native-candidates.json')
    entered = [e['pr'] for e in events if e['event'] == 'candidate_entered']
    decisions = [e for e in events if e['event'] == 'native_decision']
    validations = []
    for path in sorted(observations.glob('validation-*-pr-*.json.gz')):
        with gzip.open(path, 'rt') as handle:
            value = json.load(handle)
        validations.append({'file': str(path.relative_to(expanded)), 'pr': int(path.name.split('-pr-')[1].split('.')[0]),
                            'status': value['status'], 'reason': value.get('reason'),
                            'f2p': len(value['fail_to_pass']), 'p2p': len(value['pass_to_pass'])})
    exports = sorted(p.parent for p in (expanded / 'outputs').rglob('task.toml'))
    unchanged = load(result / 'fresh-task-files-unchanged.json', {})
    task_rows = []
    for task in exports:
        trials = {}
        for agent in ['nop', 'oracle']:
            paths = list((expanded / 'jobs/fresh' / (task.name + '-' + agent)).glob('*/result.json'))
            assert len(paths) <= 1, 'Unexpected independent trial retry'
            if not paths:
                trials[agent] = {'state': 'no_completed_trial_result', 'reward': None}
                continue
            trials[agent] = trial_evidence(paths[0], expanded)
        base, oracle = trials['nop'], trials['oracle']
        base_details, oracle_details = base.get('reward_details') or {}, oracle.get('reward_details') or {}
        verified = verified_pair(base, oracle, files_unchanged=unchanged.get('verified') is True)
        task_rows.append({'task': task.name, 'independently_verified_tracked_tests': verified,
                          'strict_oracle_command_resolved': oracle_details.get('command_resolved'),
                          'trials': trials})
    allocated = 0
    attempts = []
    for attempt in record['attempts']:
        start, end = attempt.get('started_at'), attempt.get('finished_at')
        hours = (timestamp(end) - timestamp(start)).total_seconds() * 4 / 3600 if start and end else None
        attempts.append({'started_at': start, 'finished_at': end, 'allocated_cpu_hours': hours})
        if hours is not None:
            allocated += hours
    supervisor = record.get('supervisor', {})
    row = {'repo': cohort_row['repo'], 'scientific_field': cohort_row['field_label'], 'ref': cohort_row['ref'],
        'run_id': run, 'state': record['state'], 'complete_window_merged': cohort_row['window_count'],
        'native_candidates_returned': None if candidates is None else len(candidates),
        'candidates_entered': len(entered), 'candidate_pr_numbers_entered': entered,
        'candidate_decisions': decisions, 'native_skip_reasons': dict(Counter(e['reason'] for e in decisions if e['outcome'] == 'skip')),
        'paired_validation_started': sum(e['event'] == 'validation_start' for e in events),
        'paired_validation_completed': len(validations), 'native_validation_results': validations,
        'native_validation_exceptions': [e for e in events if e['event'] == 'validation_exception'],
        'native_sandbox_nonzero': [e for e in events if e['event'] == 'sandbox_exec_end' and e['exit_code'] != 0],
        'generation_wrapper_exit_code': supervisor.get('phase_exit_code'),
        'native_cli_window': load(result / 'native-window.json'),
        'native_exports': len(exports), 'task_controls': task_rows,
        'verified_tasks': sum(t['independently_verified_tracked_tests'] for t in task_rows),
        'control_allocation_rows': load(result / 'fresh-controls.json', []),
        'task_files_unchanged': load(result / 'fresh-task-files-unchanged.json'),
        'billing': record.get('billing'), 'allocated_cpu_hours': allocated, 'attempts': attempts,
        'artifact_readback_verified': record['readback_verified'],
        'owned_cleanup_verified_empty': supervisor.get('cleanup', {}).get('verified_empty'),
        'infra_error_type': supervisor.get('error_type')}
    (result / 'assessment.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--repo')
    args = parser.parse_args()
    cohort = load(ROOT / 'cohort.json')
    if args.repo:
        cohort = [row for row in cohort if row['repo'] == args.repo]
    rows = [assess(args.state_dir, row) for row in cohort]
    print(json.dumps([{key: row.get(key) for key in ['repo', 'state', 'native_candidates_returned',
        'candidates_entered', 'paired_validation_completed', 'native_exports', 'verified_tasks',
        'billing', 'allocated_cpu_hours', 'infra_error_type']} for row in rows], indent=2))


if __name__ == '__main__':
    main()
