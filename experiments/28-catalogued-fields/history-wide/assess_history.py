"""Account for original history evidence; never execute tests, change tasks or upgrade grades."""

import argparse
from collections import Counter
import datetime
from decimal import Decimal
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def stamp(value):
    return datetime.datetime.fromisoformat(value.removeprefix('Timestamp(').removesuffix(')'))


def reconcile_identities(identities, ledger, observations):
    pending = identities.copy(); entered_all = []; omitted_all = []
    batches = []
    for row in ledger.get('batches', []):
        name = f"batch-{row['index']:04d}"
        actual = observations.get(name, {})
        chosen = row['selected_pr_numbers']
        assert chosen == pending[:100], 'Batch selection must preserve frozen remaining order'
        events = actual.get('events', [])
        returned = actual.get('returned')
        entered = [e['pr'] for e in events if e['event'] == 'candidate_entered']
        assert len(set(entered)) == len(entered)
        assert set(entered) <= set(returned or []) <= set(chosen)
        if 'native_entered_pr_numbers' in row:
            assert row['native_entered_pr_numbers'] == entered
            assert row['native_returned_pr_numbers'] == returned
        omitted = [n for n in chosen if returned is not None and n not in set(returned)]
        done = set(entered) | set(omitted)
        assert not set(entered_all + omitted_all).intersection(done)
        pending = [n for n in pending if n not in done]
        entered_all.extend(entered); omitted_all.extend(omitted)
        batches.append({'index': row['index'], 'original_state': row['state'],
            'native_cli_exit_code': row.get('exit_code'), 'selected_count': len(chosen),
            'native_list_available': returned is not None, 'native_returned': len(returned) if returned is not None else None,
            'entered': len(entered), 'native_discovery_omitted': len(omitted),
            'paired_started': sum(e['event'] == 'validation_start' for e in events),
            'validation_result_files': len(actual.get('validations', [])),
            'decisions': dict(Counter(e['outcome'] + ':' + e.get('reason', '') for e in events if e['event'] == 'native_decision')),
            'validation_exceptions': [e for e in events if e['event'] == 'validation_exception']})
    assert len(entered_all) + len(omitted_all) + len(pending) == len(identities)
    raw = ledger.get('backlog_pr_numbers', identities)
    if ledger.get('state') != 'running':
        assert raw == pending
    return {'native_entered_pr_numbers': entered_all, 'native_discovery_omitted_pr_numbers': omitted_all,
        'backlog_count': len(pending), 'backlog_sha256': hashlib.sha256(json.dumps(pending).encode()).hexdigest(),
        'original_parent_backlog_count': len(raw),
        'parent_checkpoint_censored': ledger.get('state') == 'running',
        'complete_identity_accounting': True, 'batches': batches}


def verifier_module():
    source = BASE / 'preflight/upstream_verifier.py'
    expected = read(BASE / 'preflight/upstream-verifier-source.json')['sha256']
    assert sha(source) == expected
    spec = importlib.util.spec_from_file_location('original_history_verifier', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, expected


def trial(path, task, module, expected, files_unchanged):
    result = read(path); directory = path.parent
    details = read(directory / 'verifier/reward-details.json', {})
    reported = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    reward_path = directory / 'verifier/reward.txt'
    written = float(reward_path.read_text().strip()) if reward_path.exists() else None
    exception = (result.get('exception_info') or {}).get('exception_type')
    rows = {'reward': reported, 'written_reward': written, 'exception': exception,
        'reward_details': details, 'trial_path': str(path.relative_to(task.parents[2])),
        'reward_consistent': reported is not None and written is not None and math.isfinite(written)
            and reported == written and details.get('reward') is not None
            and math.isclose(details['reward'], written, rel_tol=0, abs_tol=0.500001e-6),
        'task_files_unchanged': files_unchanged,
        'source_sha256': {str(p.relative_to(directory)): sha(p) for p in
            [path, reward_path, directory / 'verifier/reward-details.json', directory / 'verifier/test_output.log'] if p.exists()}}
    log = directory / 'verifier/test_output.log'
    verified_source = (task / 'tests/verifier.py').exists() and sha(task / 'tests/verifier.py') == expected
    rows['exact_pinned_verifier'] = verified_source
    if not log.exists() or not verified_source:
        rows['direct_audit_available'] = False
        return rows
    assert log.stat().st_size <= 32 * 1024**2, 'Use remote analysis for larger control logs'
    try:
        raw = log.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        rows.update(direct_audit_available=False, raw_log_utf8=False)
        return rows
    runner = details.get('runner')
    # For incomplete trials without recorded runner, retain the raw log without
    # inventing a grade or inferring completion from its partial status lines.
    if not runner:
        rows['direct_audit_available'] = False
        return rows
    statuses = module.parse_logs(runner, raw)
    rows.update(direct_audit_available=True, retained_status_counts=dict(Counter(statuses.values())),
        retained_test_count=len(statuses), retained_log_partial=bool(exception or reported is None))
    if reported is not None and not exception and details.get('parse_status') == 'ok':
        f2p, p2p = (read(task / ('tests/' + name + '.json')) for name in ['f2p', 'p2p'])
        original = module.grade(f2p, p2p, statuses, runner)
        assert original and statuses
        for key, value in original.items():
            assert details[key] == value, ('Original recorded grade mismatch', key)
        assert details['tests_parsed'] == len(statuses)
        command = bool(original['resolved'] and original['untracked_failed_count'] == 0 and details['exit_code'] == 0)
        assert details['command_resolved'] == command
        rows.update(original_grade_matches_raw_log=True,
            tracked_f2p_statuses=dict(Counter(statuses.get(t, 'MISSING') for t in f2p)),
            tracked_p2p_statuses=dict(Counter(statuses.get(t, 'MISSING') for t in p2p)))
    return rows


def verified(base, oracle, unchanged):
    return bool(unchanged and base.get('reward') == 0 and oracle.get('reward') == 1
        and all(r.get('reward_consistent') and r.get('original_grade_matches_raw_log')
            and r.get('exact_pinned_verifier') and not r.get('exception')
            and r.get('reward_details', {}).get('parse_status') == 'ok' for r in [base, oracle]))


def scan_phase(path, extracted):
    observations, task_hashes, bootstrap, emitted_manifests = {}, {}, [], set()
    total, names = 0, set()
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            relative = Path(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            if member.isdir():
                continue
            assert member.isfile() and member.name not in names
            names.add(member.name); total += member.size
            assert member.size < 256 * 1024**2 and total < 2 * 1024**3
            parts = relative.parts
            source = archive.extractfile(member)
            if len(parts) == 3 and parts[0] == 'native-observations':
                batch = observations.setdefault(parts[1], {'events': [], 'returned': None, 'validations': []})
                if parts[-1] == 'events.jsonl':
                    assert member.size < 16 * 1024**2
                    batch['events'] = [json.loads(line) for line in source if line.strip()]
                elif parts[-1] == 'native-candidates.json':
                    assert member.size < 16 * 1024**2
                    batch['returned'] = [row['number'] for row in json.load(source)]
                elif parts[-1].startswith('validation-') and parts[-1].endswith('.json.gz'):
                    with gzip.GzipFile(fileobj=source) as compressed:
                        raw = compressed.read(32 * 1024**2 + 1)
                    assert len(raw) <= 32 * 1024**2
                    value = json.loads(raw)
                    batch['validations'].append({'file': member.name, 'status': value['status'],
                        'reason': value.get('reason'), 'f2p': len(value['fail_to_pass']), 'p2p': len(value['pass_to_pass'])})
            elif parts[0] == 'bootstrap' and relative.name == 'bootstrap.json':
                assert member.size < 1024**2
                value = json.load(source)
                bootstrap.append({key: value.get(key) for key in ['repo', 'ref', 'language', 'test_cmds',
                    'smoke_passed', 'verify_passed', 'iterations', 'llm_cost_estimate_usd']})
            elif parts[0] == 'outputs' and len(parts) >= 4:
                task_name = '/'.join(parts[:3]); rel = '/'.join(parts[3:])
                if rel == 'task.toml':
                    emitted_manifests.add(task_name)
                if rel in ['tests/verifier.py', 'tests/f2p.json', 'tests/p2p.json', 'tests/test.sh', 'task.toml']:
                    destination = extracted / relative; destination.parent.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256()
                    with destination.open('wb') as output:
                        while chunk := source.read(1024 * 1024):
                            digest.update(chunk); output.write(chunk)
                    actual = digest.hexdigest()
                else:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                task_hashes.setdefault('/work/' + task_name, {})[rel] = actual
            elif parts[:2] == ('jobs', 'fresh') and (relative.name in
                ['result.json', 'reward.txt', 'reward-details.json', 'test_output.log', 'trial.log']):
                assert member.size <= 32 * 1024**2
                destination = extracted / relative; destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
    task_hashes = {name: hashes for name, hashes in task_hashes.items()
        if name.removeprefix('/work/') in emitted_manifests}
    return observations, task_hashes, bootstrap, sorted(emitted_manifests)


def assess(state, selected):
    run = 'biotasks28-history-' + selected['slug'].lower().replace('__', '-') + '-001'
    record = read(state / (run + '-terminal.json'))
    if not record:
        return None
    assert record['readback_verified'] and record['billing']['cost_complete']
    result = state / (run + '-results'); phase = result / 'phase-artifacts.tar.gz'
    identities = read(ROOT / 'candidate-identities' / (selected['slug'] + '.json'))['pr_numbers']
    ledger = read(result / 'history-batches.json', {'batches': [], 'state': 'not_started', 'backlog_pr_numbers': identities})
    extracted = result / 'analysis-control-files'; extracted.mkdir(exist_ok=True)
    observations, hashes, bootstrap, exports = scan_phase(phase, extracted) if phase.exists() else ({}, {}, [], [])
    coverage = reconcile_identities(identities, ledger, observations)
    unchanged = read(result / 'fresh-task-files-unchanged.json', {})
    if exports:
        assert unchanged.get('verified') and unchanged['before'] == unchanged['after'] == hashes
    module, expected = verifier_module()
    tasks = []
    for task_name in exports:
        task = extracted / task_name; name = task.name; controls = {}
        for agent in ['nop', 'oracle']:
            matches = list((extracted / 'jobs/fresh' / (name + '-' + agent)).glob('*/result.json'))
            assert len(matches) <= 1, 'No independent trial retries'
            controls[agent] = trial(matches[0], task, module, expected, unchanged.get('verified')) if matches else {'reward': None, 'state': 'no_original_trial_result'}
        primary = verified(controls['nop'], controls['oracle'], unchanged.get('verified'))
        tasks.append({'task': name, 'raw_primary_verified': primary,
            'strict_clean_verified': bool(primary and controls['oracle']['reward_details'].get('command_resolved')),
            'controls': controls})
    events = [e for b in observations.values() for e in b['events']]
    decisions = [e for e in events if e['event'] == 'native_decision']
    cpu = sum((Decimal(str((stamp(a['finished_at']) - stamp(a['started_at'])).total_seconds())) * 4 / 3600 for a in record['attempts']), Decimal('0'))
    output = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Original history evidence only; read-only accounting and exact pinned-parser/grade consistency audit. No tests, task changes, normalization, regrading, model calls or baseline-result mixing.',
        'repo': selected['repo'], 'field': selected['field_label'], 'ref': selected['ref'], 'run_id': run,
        'wrapper_state': record['state'], 'native_parent_state': ledger.get('state'),
        'native_parent_stop_reason': ledger.get('stop_reason'), 'native_supervisor_exit': record['supervisor'].get('phase_exit_code'),
        'frozen_history_identities': len(identities), 'coverage': coverage, 'bootstrap': bootstrap,
        'native_skip_reasons': dict(Counter(e['reason'] for e in decisions if e['outcome'] == 'skip')),
        'native_error_reasons': dict(Counter(e['reason'] for e in decisions if e['outcome'] == 'error')),
        'native_emission_events': [e['name'] for e in decisions if e['outcome'] == 'emit'],
        'native_exports_manifest_present': len(exports), 'task_controls': tasks,
        'raw_primary_verified_tasks': sum(t['raw_primary_verified'] for t in tasks),
        'raw_strict_clean_verified_tasks': sum(t['strict_clean_verified'] for t in tasks),
        'original_control_allocation': read(result / 'fresh-controls.json', []),
        'billing': record['billing'], 'allocated_cpu_hours': str(cpu), 'owned_cleanup_empty': record['supervisor']['cleanup']['verified_empty'],
        'original_phase_sha256': sha(phase) if phase.exists() else None,
        'standalone_verifier_sha256': expected, 'archive_acceptance_pending': True}
    output_path = ROOT / 'results' / (selected['slug'] + '.json'); output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--slug')
    args = parser.parse_args()
    cohort = read(BASE / 'cohort.json')
    if args.slug:
        cohort = [r for r in cohort if r['slug'] == args.slug]
    for selected in cohort:
        row = assess(args.state_dir, selected)
        if row:
            print(json.dumps({k: row[k] for k in ['repo', 'wrapper_state', 'frozen_history_identities',
                'native_exports_manifest_present', 'raw_primary_verified_tasks', 'raw_strict_clean_verified_tasks',
                'billing', 'allocated_cpu_hours']}), flush=True)


if __name__ == '__main__':
    main()
