"""Report the fixed cohort without treating unreported work as failure or free."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def verified(task, unchanged):
    base, oracle = (task['trials'][agent] for agent in ['nop', 'oracle'])
    return bool(unchanged and base.get('reward') == 0 and oracle.get('reward') == 1
        and all(trial.get('reward_consistent') is True
            and (trial.get('reward_details') or {}).get('parse_status') == 'ok'
            and not trial.get('exception') for trial in [base, oracle]))


def summarize(root):
    rows = []
    cost = Decimal('0')
    cpu_hours = Decimal('0')
    for selected in read(root / 'cohort.json'):
        slug = selected['slug']
        result = read(root / 'results' / (slug + '.json'))
        row = {'repo': selected['repo'], 'field': selected['field_label'],
            'complete_window_merged': selected['window_count'],
            'stage': 'not_reported', 'actual_cost_usd': None,
            'verified_tasks': None, 'evidence_accepted': False}
        if result is None:
            rows.append(row)
            continue
        assert result['repo'] == selected['repo'] and result['ref'] == selected['ref']
        count = strict = 0
        for task in result['task_controls']:
            accepted = verified(task, (result.get('task_files_unchanged') or {}).get('verified'))
            assert accepted == task['independently_verified_tracked_tests']
            count += accepted
            strict += accepted and task.get('strict_oracle_command_resolved') is True
        assert count == result['verified_tasks']
        receipt_path = root / 'archives' / (slug + '-receipt.json')
        manifest_path = root / 'archives' / (slug + '-manifest.json')
        receipt = read(receipt_path)
        archive_ok = bool(receipt and receipt.get('anonymous_download_verified')
            and manifest_path.exists()
            and hashlib.sha256(manifest_path.read_bytes()).hexdigest() == receipt['manifest_sha256'])
        billing = result.get('billing') or {}
        cost_complete = bool(billing.get('cost_complete') and not billing.get('unresolved_calls'))
        known = Decimal(billing['actual_cost_usd']) if cost_complete else None
        if known is not None:
            cost += known
        cpu_hours += Decimal(str(result['allocated_cpu_hours']))
        accepted = bool(archive_ok and result['artifact_readback_verified']
            and result['owned_cleanup_verified_empty'] and cost_complete)
        row.update(stage=result['furthest_stage_reached'],
            native_status=result['native_status'],
            native_cli_window=result.get('native_cli_window'),
            native_candidates_returned=result['native_candidates_returned'],
            candidates_entered=result['candidates_entered'],
            paired_validation_started=result['paired_validation_started'],
            paired_validation_completed=result['paired_validation_completed'],
            native_skip_reasons=result['native_skip_reasons'],
            exports=result['native_exports'], verified_tasks=count,
            strict_verified_oracle_command_resolved_tasks=strict,
            controls_reached=sum(item.get('state') != 'unstarted' for item in result['control_allocation_rows']),
            controls_unstarted=sum(item.get('state') == 'unstarted' for item in result['control_allocation_rows']),
            control_allocation_states=[{'task':item['task'], 'agent':item['agent'], 'state':item['state']}
                for item in result['control_allocation_rows']],
            actual_cost_usd=None if known is None else str(known),
            allocated_cpu_hours=result['allocated_cpu_hours'], evidence_accepted=accepted,
            archive_receipt=str(receipt_path.relative_to(root)),
            failure_or_limit=result['failure_cause'])
        rows.append(row)
    complete = bool(rows) and all(row['evidence_accepted'] for row in rows)
    published = [row for row in rows if row['evidence_accepted']]
    count = sum(row['verified_tasks'] for row in published)
    successful = sum(row['verified_tasks'] > 0 for row in published)
    return {'scope': 'Fixed ten-repository cohort only; earlier issues excluded.',
        'cohort_result_evidence_complete': complete,
        'goal_completion_not_asserted': 'Final live resource/process checks, scientific audit, issue conclusion/readback/closure and task-owned temporary cleanup are separate requirements.',
        'reported_repositories': sum(row['stage'] != 'not_reported' for row in rows),
        'evidence_accepted_repositories': len(published),
        'complete_window_merged_prs': sum(row['complete_window_merged'] for row in rows),
        'known_reported_actual_cost_usd': str(cost),
        'reported_allocated_cpu_hours': str(cpu_hours),
        'verified_tasks_with_archived_evidence': count,
        'successful_repositories_with_archived_evidence': successful,
        'cost_per_verified_task_usd': str(cost / count) if complete and count else None,
        'cost_per_successful_repository_usd': str(cost / successful) if complete and successful else None,
        'ratio_note': 'Ratios withheld until all ten have readback, cleanup and complete actual billing; zero denominators remain undefined.',
        'repositories': rows}


def display(value, *, precision=None):
    if value is None:
        return '—'
    return format(Decimal(str(value)), f'.{precision}f') if precision is not None else str(value)


def main():
    result = summarize(ROOT)
    (ROOT / 'cohort-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Fixed-cohort evidence report', '',
        'All ten selected repositories remain visible. Missing results are unreported, not zero-cost failures. '
        'Only verified archived evidence enters task/success counts. Cost ratios include failed repositories and '
        'are withheld until the complete cohort is accounted for.', '',
        '| Field / repository | Window merges | Native returned | Entered | Paired started/completed | Exports | Verified tracked | Clean verified oracle | Actual USD | Allocated CPUh | Stage |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    keys = ['complete_window_merged', 'native_candidates_returned', 'candidates_entered', 'paired',
        'exports', 'verified_tasks', 'strict_verified_oracle_command_resolved_tasks',
        'actual_cost_usd', 'allocated_cpu_hours', 'stage']
    for row in result['repositories']:
        cells = []
        for key in keys:
            if key == 'paired':
                cells.append(display(row.get('paired_validation_started')) + '/'
                    + display(row.get('paired_validation_completed')))
            else:
                precision = 3 if key == 'allocated_cpu_hours' else 6 if key == 'actual_cost_usd' else None
                cells.append(display(row.get(key), precision=precision))
        lines.append('| ' + row['field'] + ' / ' + row['repo'] + ' | '
            + ' | '.join(cells) + ' |')
    lines += ['', 'Cohort result evidence complete: ' + str(result['cohort_result_evidence_complete']) + '.', '',
        result['goal_completion_not_asserted'], '',
        'Reported actual model cost: $' + result['known_reported_actual_cost_usd']
        + '; reported allocated CPU-hours: ' + display(result['reported_allocated_cpu_hours'], precision=6) + '.', '',
        'Verified tasks / successful repositories with archived evidence: '
        + str(result['verified_tasks_with_archived_evidence']) + ' / '
        + str(result['successful_repositories_with_archived_evidence']) + '.', '',
        'Full-cohort cost per verified task: ' + display(result['cost_per_verified_task_usd'], precision=6)
        + '; per successful repository: ' + display(result['cost_per_successful_repository_usd'], precision=6) + '.', '',
        'Window inventory is not a processed-PR denominator. A tracked-test oracle reward of one '
        'does not establish whole-command resolution, exact-image replay or release readiness.', '']
    for row in result['repositories']:
        if row['stage'] == 'not_reported':
            continue
        lines += ['## ' + row['repo'], '', row['failure_or_limit'], '',
            'Native skip reasons: ' + json.dumps(row['native_skip_reasons'], sort_keys=True)
            + '. Controls reached/unstarted: ' + str(row['controls_reached']) + '/'
            + str(row['controls_unstarted']) + '. Archive accepted: ' + str(row['evidence_accepted']) + '.', '']
    (ROOT / 'cohort-report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in result.items() if k != 'repositories'}, indent=2))


if __name__ == '__main__':
    main()
