"""Read-only original history accounting; partial audits never establish cohort completion."""

import argparse
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib

import cost_guard
from payload import BASE, ROOT, build
from retention import PUBLIC_BUCKET, verified_receipt


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def stamp(value):
    return datetime.datetime.fromisoformat(value.removeprefix('Timestamp(').removesuffix(')'))


def phase_records(path):
    """Retain only small audit records, streaming over original unmodified evidence."""
    records, expanded, names = {}, 0, set()
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            if member.isdir():
                continue
            assert member.isfile() and member.name not in names
            names.add(member.name); expanded += member.size
            assert expanded <= 64 * 1024**2, 'Larger audits require appropriately sized compute'
            parts = Path(member.name).parts
            relevant = (parts[:1] == ('infra',) and parts[-1] in
                ['history-identities.json', 'history-run-budget.json']) or (
                len(parts) == 3 and parts[0] == 'native-observations' and
                (parts[-1] in ['events.jsonl', 'billing.json'] or
                 parts[-1].startswith(('cost-quote-', 'generation-'))))
            if not relevant:
                continue
            assert member.size <= 16 * 1024**2
            source = archive.extractfile(member)
            records[member.name] = ([json.loads(line) for line in source if line.strip()]
                if parts[-1] == 'events.jsonl' else json.load(source))
    return records


def audit_calls(records, remaining):
    total, count, previous_charge_time = Decimal('0'), 0, None
    reports, response_ids = [], set()
    batches = sorted({Path(name).parts[1] for name in records if name.startswith('native-observations/')})
    for batch in batches:
        root = 'native-observations/' + batch + '/'
        events, snapshot = records.get(root + 'events.jsonl', []), records.get(root + 'billing.json')
        assert snapshot and snapshot['cost_complete'] and not snapshot['shared_account_deltas_used']
        batch_cost, calls, charged, pending, reserved, response = Decimal('0'), set(), set(), None, None, None
        for event in events:
            name = event['event']
            if name == 'campaign_cost_reservation':
                assert pending is None
                available = remaining - total - batch_cost
                assert available == Decimal(event['available_usd'])
                quote = records[root + f'cost-quote-{len(calls) + 1:03d}.json']
                amount = cost_guard.reservation(quote, 2048)
                assert amount == Decimal(event['reserved_usd'])
                assert event['allowed'] == (available >= amount)
                reserved = (amount, event['time']) if event['allowed'] else None
            elif name == 'model_request':
                call = event['call']
                assert pending is None and call == len(calls) + 1 and reserved is not None
                assert total + batch_cost < Decimal('5') and count + len(calls) < 20
                assert event['model'] == 'openrouter/anthropic/claude-sonnet-4.6'
                assert event['max_tokens'] == 2048 and event['temperature'] == 0.2
                assert reserved[1] <= event['time']
                assert previous_charge_time is None or event['time'] >= previous_charge_time
                pending = (call, reserved[0], event['time']); reserved = None; calls.add(call)
            elif name == 'model_response':
                assert pending is not None and event['call'] == pending[0] and response is None
                assert event['response_id'] and event['response_id'] not in response_ids
                response_ids.add(event['response_id']); response = event
            elif name == 'model_charge':
                assert pending is not None and event['call'] == pending[0] and event['call'] not in charged
                charge = Decimal(event['actual_cost_usd'])
                assert charge.is_finite() and Decimal('0') <= charge <= pending[1]
                assert event['time'] >= pending[2]
                assert response is not None
                if event['source'] == 'response.usage.cost':
                    assert charge == Decimal(str(response['usage']['cost']))
                else:
                    assert event['source'] == 'generation.total_cost'
                    generation = records[root + f'generation-{pending[0]:03d}.json']
                    assert generation['id'] == response['response_id']
                    assert charge == Decimal(str(generation['total_cost']))
                batch_cost += charge
                assert batch_cost == Decimal(event['cumulative_actual_usd'])
                charged.add(event['call']); pending = None; response = None; previous_charge_time = event['time']
            elif name == 'validation_start':
                assert event['timeout'] == 600
        assert pending is None and calls == charged
        assert batch_cost == Decimal(snapshot['actual_cost_usd']) and len(calls) == snapshot['model_calls']
        assert Decimal(snapshot['stop_threshold_usd']) == max(Decimal('0'), Decimal('5') - total)
        reports.append({'batch': batch, 'model_calls': len(calls), 'actual_cost_usd': str(batch_cost)})
        total += batch_cost; count += len(calls)
    assert count <= 20 and total <= remaining
    return {'model_calls': count, 'actual_cost_usd': str(total), 'all_dispatched_calls_reconciled': True,
        'per_call_reservations_recomputed': True, 'batches': reports}


def audit_repo(state, selected, remaining, client, *, retention_required=True):
    run = 'biotasks28-history-' + selected['slug'].lower().replace('__', '-') + '-001'
    terminal = read(state / (run + '-terminal.json'))
    receipt = read(state / (run + '-receipt.json'))
    result_dir = state / (run + '-results')
    assessment_path = ROOT / 'results' / (selected['slug'] + '.json')
    result = read(assessment_path)
    manifest_path = ROOT / 'archives' / (selected['slug'] + '-manifest.json')
    manifest = read(manifest_path)
    published_path = ROOT / 'archives' / (selected['slug'] + '-receipt.json')
    published = read(published_path) if published_path.exists() else None
    archive_ok = published is not None
    if archive_ok:
        assert verified_receipt(published, manifest) and sha(manifest_path) == published['manifest_sha256']
    assert archive_ok or not retention_required, 'Verified retention is required for full accounting'
    assert terminal['readback_verified'] and terminal['billing']['cost_complete'] and not terminal['billing']['unresolved_calls']
    assert receipt['job_id'] == '/exedev/' + run and receipt['repo_ref'] == selected['ref']
    assert not receipt['new_capacity'] and receipt['attempts_allowed'] == 1
    assert Decimal(receipt['remaining_openrouter_usd']) == remaining
    assert receipt['cpu'] == 4 and receipt['memory_gib'] == 16 and receipt['disk_gib'] == 30
    assert receipt['timeout_seconds'] == 9000
    expected = build(selected, remaining)
    assert receipt['input_sha256'] == {name: hashlib.sha256(raw).hexdigest() for name, raw in expected.items()}
    reference = next(r for r in read(ROOT / 'payload-manifest.json')['reference_payloads'] if r['repo'] == selected['repo'])
    assert all(receipt['input_sha256'][name] == digest for name, digest in reference['payload_sha256'].items()
        if name != 'history-run-budget.json')
    assert len(terminal['attempts']) == 1
    attempt = terminal['attempts'][0]
    assert attempt['worker_id'] == receipt['worker_id'] and attempt['state'] in ['succeeded', 'failed', 'killed']
    start, finish = stamp(attempt['started_at']), stamp(attempt['finished_at'])
    duration = finish - start
    seconds = Decimal(duration.days * 86400 + duration.seconds) + Decimal(duration.microseconds) / 1000000
    assert Decimal('0') <= seconds <= 9000
    supervisor = read(result_dir / 'supervisor-result.json')
    assert supervisor == terminal['supervisor'] and supervisor['cleanup']['verified_empty']
    assert all(not rows for rows in supervisor['cleanup']['remaining'].values())
    if 'controls_started' in supervisor:
        assert supervisor['native_finished'] <= supervisor['controls_started']
        assert 0 < supervisor['controls_window_seconds'] <= 3600
        if 'controls_finished' in supervisor:
            assert supervisor['controls_finished'] - supervisor['controls_started'] <= supervisor['controls_window_seconds'] + 30
    if supervisor.get('phase_started'):
        installation = (result_dir / 'installation.log').read_text()
        assert all(text in installation for text in ['/work/source.tar.gz: OK', 'repo2rlenv 0.9.3', 'Native configurations validated'])
    phase = result_dir / 'phase-artifacts.tar.gz'
    phase_row = next((r for r in manifest['files'] if r['path'] == 'evidence/phase-artifacts.tar.gz'), None)
    if phase.exists():
        assert phase_row and sha(phase) == phase_row['sha256'] == result['original_phase_sha256']
        records = phase_records(phase)
        calls = audit_calls(records, remaining)
        if records.get('infra/history-run-budget.json'):
            assert hashlib.sha256((json.dumps(records['infra/history-run-budget.json'], indent=2) + '\n').encode()).hexdigest() == receipt['input_sha256']['history-run-budget.json']
            assert records['infra/history-identities.json'] == json.loads(expected['history-identities.json'])
    else:
        assert not supervisor.get('phase_started') and not phase_row and result['original_phase_sha256'] is None
        calls = {'model_calls': 0, 'actual_cost_usd': '0', 'all_dispatched_calls_reconciled': True, 'batches': []}
    assert Decimal(calls['actual_cost_usd']) == Decimal(terminal['billing']['actual_cost_usd']) == Decimal(result['billing']['actual_cost_usd'])
    assert calls['model_calls'] == terminal['billing']['model_calls'] == result['billing']['model_calls']
    unchanged_path = result_dir / 'fresh-task-files-unchanged.json'
    if unchanged_path.exists():
        unchanged = read(unchanged_path)
        assert unchanged['verified'] and unchanged['before'] == unchanged['after']
    else:
        assert not result['native_exports_manifest_present'] and 'controls_started' not in supervisor
    verifier_timeouts = {}
    for original, files in (unchanged['before'] if unchanged_path.exists() else {}).items():
        task_path = result_dir / 'analysis-control-files' / Path(original).relative_to('/work') / 'task.toml'
        assert sha(task_path) == files['task.toml']
        timeout = tomllib.loads(task_path.read_text())['verifier']['timeout_sec']
        assert timeout == 300
        verifier_timeouts[task_path.parent.name] = timeout
    controls_path = result_dir / 'fresh-controls.json'
    controls = read(controls_path) if controls_path.exists() else []
    if not controls_path.exists():
        assert not result['native_exports_manifest_present'] and 'controls_started' not in supervisor
    assert len({(r['task'], r['agent']) for r in controls}) == len(controls)
    previous_control_finish = None
    for control in controls:
        assert control['agent'] in ['nop', 'oracle']
        if 'command' not in control:
            assert control['state'] == 'unstarted'
            continue
        command = control['command']
        for flag, value in [('-a', control['agent']), ('--env', 'docker'), ('-n', '1'), ('-k', '1'),
                ('-r', '0'), ('--override-cpus', '1'), ('--override-memory-mb', '6144')]:
            assert command[command.index(flag) + 1] == value
        assert '--verifier-timeout-multiplier' not in command
        assert control['started'] >= supervisor['controls_started']
        assert control['started'] < supervisor['controls_started'] + supervisor['controls_window_seconds']
        assert previous_control_finish is None or control['started'] >= previous_control_finish
        previous_control_finish = control.get('finished')
    from iris.cluster.types import JobName
    from iris.resources.state import is_job_finished
    job = client.job(JobName.from_string(receipt['job_id']))
    status, task = job.status(), job.task(0).describe()
    assert is_job_finished(status.state) and status.state.name == terminal['state']
    assert len(task.status.attempts) == 1 and task.status.attempts[0].attempt_uid == attempt['attempt_uid']
    assert task.resources.cpu_millicores == 4000 and task.resources.memory_bytes == 16 * 1024**3
    assert task.resources.disk_bytes == 30 * 1024**3 and task.resources.device is None
    return {'repo': selected['repo'], 'run_id': run, 'live_terminal_state': status.state.name,
        'original_attempts': 1, 'static_and_dynamic_payload_hashes_match': True,
        'source_revision': read(BASE / 'pins.json')['source_revision'], 'source_archive_checksum_verified_during_install': bool(supervisor.get('phase_started')),
        'model_accounting': calls, 'started_at': start.isoformat(), 'finished_at': finish.isoformat(),
        'allocated_cpu_hours': str(seconds * 4 / 3600), 'owned_cleanup_verified_empty': True,
        'actual_control_commands_audited': sum('command' in row for row in controls),
        'original_control_rows_audited': len(controls),
        'original_controls_unstarted': sum('command' not in row for row in controls),
        'task_byte_audit_in_assessment': sha(assessment_path),
        'actual_exported_verifier_timeouts_seconds': verifier_timeouts,
        'archive_receipt_accepted': archive_ok, 'original_phase_sha256': result['original_phase_sha256'],
        'archive_bucket': (published or manifest).get('bucket', manifest.get('archive_bucket', PUBLIC_BUCKET)),
        'archive_visibility': (published or manifest).get('visibility', manifest.get('archive_visibility', 'public')),
        'archive_manifest_sha256': sha(manifest_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--slug', help='Audit one terminal repository; never declare the cohort complete')
    parser.add_argument('--execution-only', action='store_true',
        help='Audit original execution/cost/resource records separately; never assert full retention/accounting acceptance')
    args = parser.parse_args()
    cohort = read(BASE / 'cohort.json'); assert len(cohort) == 10
    if args.slug:
        assert args.slug in {r['slug'] for r in cohort}
    else:
        assert all((args.state_dir / ('biotasks28-history-' + r['slug'].lower().replace('__', '-') + '-001-terminal.json')).exists() for r in cohort)
    from iris.cli.connect import connect_controller
    from iris.client.client import IrisClient
    reports, previous_finish, remaining = [], None, Decimal('94.024714')
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            for selected in cohort:
                run = 'biotasks28-history-' + selected['slug'].lower().replace('__', '-') + '-001'
                path = args.state_dir / (run + '-terminal.json')
                if args.slug and args.slug != selected['slug']:
                    if path.exists():
                        prior = read(path); assert prior['billing']['cost_complete']
                        remaining -= Decimal(prior['billing']['actual_cost_usd'])
                        previous_finish = stamp(prior['attempts'][0]['finished_at'])
                    continue
                row = audit_repo(args.state_dir, selected, remaining, client, retention_required=not args.execution_only)
                assert previous_finish is None or datetime.datetime.fromisoformat(row['started_at']) >= previous_finish
                previous_finish = datetime.datetime.fromisoformat(row['finished_at'])
                remaining -= Decimal(row['model_accounting']['actual_cost_usd'])
                assert remaining >= 0
                reports.append(row)
                print(json.dumps(row), flush=True)
                if args.slug:
                    break
    execution_complete = len(reports) == 10 and not args.slug
    complete = execution_complete and not args.execution_only
    output = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'audit_source_sha256': sha(Path(__file__)), 'all_ten_accounting_audited': complete,
        'all_ten_execution_audited': execution_complete,
        'execution_only': args.execution_only,
        'all_ten_retention_audited': execution_complete and all(row['archive_receipt_accepted'] for row in reports),
        'unaccepted_archive_repositories': [row['repo'] for row in reports if not row['archive_receipt_accepted']],
        'scope': ('Execution-only original payload/source/charge/reservation/serial-control/terminal/resource audit; missing retention remains unaccepted. Not full accounting, issue completion or a retention waiver.'
            if args.execution_only else 'Original payload/source/charges/reservations/serial controls/terminal handles/resources/retention accounting. Scientific assessment, fresh archive recheck, lifecycle cleanup and publication remain separate.'),
        'repositories': reports}
    if execution_complete:
        cpu = sum((Decimal(r['allocated_cpu_hours']) for r in reports), Decimal('0'))
        assert cpu <= 100
        output.update(history_actual_cost_usd=str(Decimal('94.024714') - remaining),
            total_issue_actual_cost_usd=str(Decimal('100') - remaining), history_allocated_cpu_hours=str(cpu))
    target = ROOT / 'accounting' / ((args.slug or 'all-ten') + ('-execution-only' if args.execution_only else '') + '.json')
    target.parent.mkdir(exist_ok=True); target.write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
