"""Report the full frozen history cohort; missing evidence is never zero yield or free."""

from decimal import Decimal
from collections import Counter
import hashlib
import json
from pathlib import Path

from assess_history import verified
from retention import PUBLIC_BUCKET, verified_receipt

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(root):
    cohort = read(root.parent / 'cohort.json')
    rows, cost, cpu = [], Decimal('0'), Decimal('0')
    final = read(root / 'accounting/all-ten.json') or {}
    for selected in cohort:
        slug = selected['slug']; path = root / 'results' / (slug + '.json')
        identities = read(root / 'candidate-identities' / (slug + '.json'))
        row = {'repo': selected['repo'], 'field': selected['field_label'],
            'history_inventory': len(identities['pr_numbers']), 'stage': 'result_pending',
            'native_entered': None, 'native_backlog': None, 'exports': None,
            'primary_verified': None, 'strict_clean_verified': None,
            'actual_cost_usd': None, 'evidence_accepted': False}
        result = read(path)
        if result is None:
            rows.append(row); continue
        assert result['repo'] == selected['repo'] and result['ref'] == selected['ref']
        assert result['frozen_history_identities'] == row['history_inventory']
        coverage = result['coverage']
        entered = len(coverage['native_entered_pr_numbers']); omitted = len(coverage['native_discovery_omitted_pr_numbers'])
        assert coverage['complete_identity_accounting'] and entered + omitted + coverage['backlog_count'] == row['history_inventory']
        primary = clean = overlap = overlap_verified = 0
        for task in result['task_controls']:
            base, oracle = (task['controls'][agent] for agent in ['nop', 'oracle'])
            accepted = verified(base, oracle, base.get('task_files_unchanged') and oracle.get('task_files_unchanged'))
            assert accepted == task['raw_primary_verified']
            strict = bool(accepted and oracle['reward_details'].get('command_resolved'))
            assert strict == task['strict_clean_verified']
            primary += accepted; clean += strict
            same = task['also_exported_in_september_baseline']
            overlap += same; overlap_verified += bool(same and accepted)
        assert primary == result['raw_primary_verified_tasks']
        assert clean == result['raw_strict_clean_verified_tasks']
        assert len(result['task_controls']) == result['native_exports_manifest_present']
        manifest_path = root / 'archives' / (slug + '-manifest.json')
        manifest, receipt = read(manifest_path), read(root / 'archives' / (slug + '-receipt.json'))
        archive_ok = bool(manifest and receipt and verified_receipt(receipt, manifest)
            and sha(manifest_path) == receipt['manifest_sha256'])
        if archive_ok and result['original_phase_sha256'] is not None:
            if manifest.get('archive_kind') == 'curated_public_with_local_originals':
                local_path = root / 'archives' / (slug + '-local-originals-receipt.json')
                local = read(local_path)
                assert local and sha(local_path) == manifest['local_originals_receipt_sha256']
                assert local['original_phase_sha256'] == manifest['original_phase_sha256'] == result['original_phase_sha256']
            else:
                phase = next(r for r in manifest['files'] if r['path'] == 'evidence/phase-artifacts.tar.gz')
                assert phase['sha256'] == result['original_phase_sha256']
        accounting = read(root / 'accounting' / (slug + '.json'))
        audited = accounting['repositories'] if accounting else final.get('repositories', [])
        matching = [r for r in audited if r['repo'] == selected['repo']]
        assert len(matching) <= 1
        accounting_ok = bool(matching and archive_ok
            and matching[0]['task_byte_audit_in_assessment'] == sha(path)
            and matching[0]['archive_manifest_sha256'] == receipt['manifest_sha256']
            and matching[0]['original_phase_sha256'] == result['original_phase_sha256'])
        billing = result['billing']
        known = Decimal(billing['actual_cost_usd']) if billing['cost_complete'] and not billing['unresolved_calls'] else None
        if known is not None:
            assert known.is_finite() and known >= 0; cost += known
        allocated = Decimal(result['allocated_cpu_hours']); cpu += allocated
        controls = result['original_control_allocation']
        pairs_started = sum(r['paired_started'] for r in coverage['batches'])
        pairs_completed = sum(r['validation_result_files'] for r in coverage['batches'])
        assert pairs_completed <= pairs_started
        exceptions = [event for batch in coverage['batches'] for event in batch.get('validation_exceptions', [])]
        validation_errors = Counter(event['exception_type'] +
            ('/errno' + str(event['errno']) if event.get('errno') is not None else '') for event in exceptions)
        cli_errors = Counter(batch['original_cli_exception_type'] for batch in coverage['batches']
            if batch.get('original_cli_exception_type'))
        stage = ('independent_controls' if any('command' in r for r in controls) else
            'export' if result['native_exports_manifest_present'] else
            'paired_validation' if pairs_started else 'native_entry' if entered else
            'native_discovery' if coverage['native_list_available'] else 'setup_or_bootstrap')
        row.update(stage=stage, wrapper_state=result['wrapper_state'], native_parent_state=result['native_parent_state'],
            original_retention=('curated public + protected local originals'
                if manifest and manifest.get('archive_kind') == 'curated_public_with_local_originals' else 'HF original archive' if archive_ok else 'pending'),
            native_stop_reason=result['native_parent_stop_reason'],
            native_unique_returned=coverage['native_unique_returned_count'],
            native_returned_appearances=coverage['native_returned_appearances'], native_entered=entered,
            original_discovery_omitted=omitted, native_backlog=coverage['backlog_count'],
            native_skip_reasons=result['native_skip_reasons'], native_error_reasons=result['native_error_reasons'],
            native_validation_exception_counts=dict(validation_errors), native_cli_exception_counts=dict(cli_errors),
            entered_without_decision=sum(len(r['entered_without_native_decision']) for r in coverage['batches']),
            paired_started=pairs_started, paired_completed=pairs_completed,
            native_stage_timeouts=sum(r['exit_code'] == 124 and r['stderr_timeout_marker'] for r in result.get('native_stage_executions', [])),
            exports_with_native_stage_timeouts=sum(t.get('native_stage_timeouts', 0) > 0 for t in result['task_controls']),
            exports=result['native_exports_manifest_present'], primary_verified=primary, strict_clean_verified=clean,
            baseline_overlap_exports=overlap, baseline_overlap_primary_verified=overlap_verified,
            controls_started=sum('command' in r for r in controls),
            controls_unstarted=sum('command' not in r for r in controls),
            control_exceptions=[{'task': t['task'], 'agent': a, 'exception': v.get('exception'), 'reward': v.get('reward')}
                for t in result['task_controls'] for a,v in t['controls'].items() if v.get('exception') or v.get('reward') is None],
            actual_cost_usd=str(known) if known is not None else None, allocated_cpu_hours=str(allocated),
            archive_accepted=archive_ok, accounting_accepted=accounting_ok,
            archive_bucket=receipt.get('bucket', PUBLIC_BUCKET) if receipt else None,
            archive_visibility=receipt.get('visibility', 'public') if receipt else None,
            evidence_accepted=bool(archive_ok and accounting_ok and known is not None and result['owned_cleanup_empty']))
        rows.append(row)
    accepted = [r for r in rows if r['evidence_accepted']]
    complete = len(rows) == 10 and len(accepted) == 10
    verified_count = sum(r['primary_verified'] for r in accepted)
    successful = sum(r['primary_verified'] > 0 for r in accepted)
    return {'scope': 'Same ten catalogued fields; full frozen merged-PR history, no lower date cutoff. September baseline is separate.',
        'all_ten_result_evidence_complete': complete,
        'completion_not_asserted': 'Result-evidence acceptance alone does not assert issue completion. Accounting, retention readback, cleanup and publication/closure are checked separately in completion-audit.md.',
        'history_inventory': sum(r['history_inventory'] for r in rows),
        'result_repositories': sum(r['stage'] != 'result_pending' for r in rows),
        'accepted_result_repositories': len(accepted),
        'known_terminal_history_cost_usd': str(cost), 'reported_history_allocated_cpu_hours': str(cpu),
        'september_baseline_actual_cost_usd': '5.975286',
        'known_terminal_issue_cost_usd': str(cost + Decimal('5.975286')),
        'all_ten_costs_reported': len(rows) == 10 and all(r['actual_cost_usd'] is not None for r in rows),
        'active_and_unreported_costs_excluded': any(r['actual_cost_usd'] is None for r in rows),
        'primary_verified_tasks_with_accepted_evidence': verified_count,
        'strict_clean_tasks_with_accepted_evidence': sum(r['strict_clean_verified'] for r in accepted),
        'new_to_baseline_primary_verified_with_accepted_evidence': sum(r['primary_verified'] - r['baseline_overlap_primary_verified'] for r in accepted),
        'cost_per_verified_task_usd': str(cost / verified_count) if complete and verified_count else None,
        'cost_per_successful_repository_usd': str(cost / successful) if complete and successful else None,
        'ratios': 'Full-cohort ratios must include all ten failures/attempts and require complete evidence; zero denominators remain undefined. Inventory is not an eligible or validated-task denominator.',
        'exception_counts': 'Validation and CLI exception channels can describe the same failure and must not be added together; censored candidates remain separate.',
        'repositories': rows}


def main():
    result = summarize(ROOT)
    (ROOT / 'cohort-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# History-wide cohort evidence', '',
        'All ten repositories remain visible. Pending is not zero yield or free. '
        'Unique native-returned PRs differ from repeated metadata appearances; '
        'the frozen inventory is not a suitable-task or validated-task denominator. '
        'Entered, discovery-omitted and backlog identities partition that inventory. '
        'A PR returned earlier can still be omitted by a later listing before entry. '
        'History evidence stays separate from the September baseline.', '',
        '| Repository | Inventory | Unique returned | Entered | Discovery omitted | Backlog | Paired started/completed | Exports | Tracked verified | Clean verified | Terminal USD | Retention | Evidence accepted |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
    def display(value):
        return '—' if value is None else str(value)
    for row in result['repositories']:
        cells = [row.get(k) for k in ['repo', 'history_inventory', 'native_unique_returned', 'native_entered', 'original_discovery_omitted', 'native_backlog']]
        cells += [display(row.get('paired_started')) + '/' + display(row.get('paired_completed'))]
        cells += [row.get(k) for k in ['exports', 'primary_verified', 'strict_clean_verified', 'actual_cost_usd', 'original_retention', 'evidence_accepted']]
        lines.append('| ' + ' | '.join(display(value) for value in cells) + ' |')
    lines += ['', 'Result evidence complete: ' + str(result['all_ten_result_evidence_complete']) + '.', '',
        'Known terminal history charges: $' + result['known_terminal_history_cost_usd'] + '. '
        'All ten costs reported: ' + str(result['all_ten_costs_reported']) + '. '
        'Repositories with active/unreported charges excluded: ' + str(result['active_and_unreported_costs_excluded']) + '.', '',
        result['completion_not_asserted'], '']
    for row in result['repositories']:
        if row.get('native_validation_exception_counts') or row.get('native_cli_exception_counts'):
            lines += [row['repo'] + ': original validation exceptions ' + json.dumps(row.get('native_validation_exception_counts', {}))
                + '; original CLI exceptions ' + json.dumps(row.get('native_cli_exception_counts', {})) + '.', '']
    lines += [result['exception_counts'], '']
    (ROOT / 'cohort-report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in result.items() if k != 'repositories'}, indent=2))


if __name__ == '__main__':
    main()
