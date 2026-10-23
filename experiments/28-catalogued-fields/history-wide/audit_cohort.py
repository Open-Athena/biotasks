"""Reconcile all ten original assessments; this does not waive missing retention."""

from collections import Counter
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    cohort = read(ROOT.parent / 'cohort.json')
    execution_path = ROOT / 'accounting/all-ten-execution-only.json'
    execution = read(execution_path)
    assert len(cohort) == 10 and execution['all_ten_execution_audited']
    assert execution['audit_source_sha256'] == sha(ROOT / 'audit_accounting.py')
    totals, fields, records, positive, unclean = Counter(), {}, [], [], []
    previous_finish = None
    for selected, audited in zip(cohort, execution['repositories'], strict=True):
        slug = selected['slug']
        assessment_path = ROOT / 'results' / (slug + '.json')
        result = read(assessment_path)
        assert result['repo'] == selected['repo'] == audited['repo']
        assert result['ref'] == selected['ref']
        assert sha(assessment_path) == audited['task_byte_audit_in_assessment']
        assert result['original_phase_sha256'] == audited['original_phase_sha256']
        assert audited['original_attempts'] == 1 and audited['owned_cleanup_verified_empty']
        assert audited['static_and_dynamic_payload_hashes_match']
        start = datetime.datetime.fromisoformat(audited['started_at'])
        finish = datetime.datetime.fromisoformat(audited['finished_at'])
        assert previous_finish is None or start >= previous_finish
        previous_finish = finish
        identities_path = ROOT / 'candidate-identities' / (slug + '.json')
        identities = read(identities_path)['pr_numbers']
        coverage = result['coverage']
        entered = coverage['native_entered_pr_numbers']
        omitted = coverage['native_discovery_omitted_pr_numbers']
        assert len(set(identities)) == len(identities) == result['frozen_history_identities']
        assert len(entered) == len(set(entered)) and len(omitted) == len(set(omitted))
        assert not set(entered) & set(omitted)
        assert set(entered + omitted) <= set(identities)
        pending = [n for n in identities if n not in set(entered + omitted)]
        assert len(pending) == coverage['backlog_count']
        assert hashlib.sha256(json.dumps(pending).encode()).hexdigest() == coverage['backlog_sha256']
        assert coverage['complete_identity_accounting']
        totals.update(inventory=len(identities), entered=len(entered), omitted=len(omitted), backlog=len(pending))
        totals.update(exports=len(result['task_controls']), primary=result['raw_primary_verified_tasks'],
            clean=result['raw_strict_clean_verified_tasks'], calls=audited['model_accounting']['model_calls'],
            controls_completed=audited['actual_control_commands_audited'],
            controls_unstarted=audited['original_controls_unstarted'])
        assert len(result['task_controls']) == result['native_exports_manifest_present']
        assert sum(t['raw_primary_verified'] for t in result['task_controls']) == result['raw_primary_verified_tasks']
        assert sum(t['strict_clean_verified'] for t in result['task_controls']) == result['raw_strict_clean_verified_tasks']
        for batch in coverage['batches']:
            totals.update(paired_started=batch['paired_started'], paired_returned=batch['validation_result_files'])
            totals['errno7'] += sum(e.get('errno') == 7 for e in batch.get('validation_exceptions', []))
        field = fields.setdefault(selected['field_label'], {'primary': 0, 'clean': 0})
        field['primary'] += result['raw_primary_verified_tasks']
        field['clean'] += result['raw_strict_clean_verified_tasks']
        for task in result['task_controls']:
            if not task['raw_primary_verified']:
                assert not task['strict_clean_verified']
                continue
            base, oracle = (task['controls'][agent] for agent in ['nop', 'oracle'])
            for trial in [base, oracle]:
                assert trial['exception'] is None and not trial['retained_log_partial']
                assert all(trial[k] for k in ['reward_consistent', 'task_files_unchanged',
                    'exact_pinned_verifier', 'original_grade_matches_raw_log'])
            assert base['reward'] == 0 and oracle['reward'] == 1
            assert set(base['tracked_f2p_statuses']) == {'FAILED'}
            assert set(base['tracked_p2p_statuses']) == {'PASSED'}
            assert set(oracle['tracked_f2p_statuses']) == {'PASSED'}
            assert set(oracle['tracked_p2p_statuses']) == {'PASSED'}
            assert set(base['reward_details']['untracked_failed']) == set(oracle['reward_details']['untracked_failed'])
            assert oracle['reward_details']['command_resolved'] == task['strict_clean_verified']
            assert not task['also_exported_in_september_baseline']
            positive.append(task['task'])
            if not task['strict_clean_verified']:
                unclean.append(task['task'])
        records.append({'repo': selected['repo'], 'assessment_sha256': sha(assessment_path),
            'identities_sha256': sha(identities_path), 'original_phase_sha256': result['original_phase_sha256']})
    assert totals['entered'] + totals['omitted'] + totals['backlog'] == totals['inventory']
    assert totals['controls_completed'] + totals['controls_unstarted'] == 2 * totals['exports']
    assert len(positive) == totals['primary'] and len(unclean) == totals['primary'] - totals['clean']
    costs = sum((Decimal(r['model_accounting']['actual_cost_usd']) for r in execution['repositories']), Decimal(0))
    cpu = sum((Decimal(r['allocated_cpu_hours']) for r in execution['repositories']), Decimal(0))
    assert costs == Decimal(execution['history_actual_cost_usd'])
    assert costs + Decimal('5.975286') == Decimal(execution['total_issue_actual_cost_usd']) <= 100
    assert cpu == Decimal(execution['history_allocated_cpu_hours']) <= 100
    runtime = []
    for selected in cohort:
        path = ROOT / 'results' / (selected['slug'] + '-full-runtime-equivalence.json')
        if path.exists():
            value = read(path)
            assert value['source_assessment_sha256'] == sha(ROOT / 'results' / (selected['slug'] + '.json'))
            assert value['all_original_task_files_unchanged']
            runtime.append({'repo': selected['repo'], 'report_sha256': sha(path),
                'primary_groups': value['runtime_groups_with_primary_success'],
                'clean_groups': value['runtime_groups_with_clean_success']})
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'All-ten execution/scientific reconciliation, original assessment/raw-log bindings. Missing retention is not accepted; no native/model execution, semantic deduplication or release claim.',
        'source_sha256': sha(Path(__file__)), 'execution_audit_sha256': sha(execution_path),
        'totals': dict(totals), 'history_actual_usd': str(costs),
        'issue_actual_usd_including_september': str(costs + Decimal('5.975286')),
        'native_allocated_cpu_hours': str(cpu), 'fields': fields,
        'all_positive_pairs_have_failed_base_f2p_passed_base_p2p_and_passed_oracle_tracked_tests': True,
        'unclean_positive_pairs_with_identical_base_oracle_untracked_failures': unclean,
        'runtime_equivalence': runtime, 'repositories': records,
        'unaccepted_archives': execution['unaccepted_archive_repositories'],
        'full_retention_or_completion_claimed': False}
    (ROOT / 'accounting/all-ten-scientific-reconciliation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['totals', 'history_actual_usd', 'issue_actual_usd_including_september', 'unaccepted_archives']}))


if __name__ == '__main__':
    main()
