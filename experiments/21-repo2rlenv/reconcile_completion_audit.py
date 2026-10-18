"""Reconcile closeout evidence without relabeling historical protocol gaps as met."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    sources = {}

    def read(name):
        raw = (ROOT / name).read_bytes()
        assert len(raw) <= 16 * 1024**2
        sources[name] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    census = read('evidence/campaign-census-20261018/census.json')
    traffic = read('evidence/usage-reconciliation-20261018/usage.json')
    retention = read('evidence/artifact-retention-reconciliation-20261018/local-manifest-receipt-audit.json')
    timing = read('evidence/controller-timing-reconciliation-20261018/campaign-controller-times.json')
    presence = read('evidence/final-resource-observation-20261018/presence.json')
    budget = read('budget-reconciliation-20261016.json')
    for record in (census, traffic):
        for name, digest in record['source_sha256'].items():
            raw = (ROOT / name).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == digest, name
    units = census['units']
    assert len({u['unit_id'] for u in units}) == census['scope_entries']
    admitted = sum(u['current_admitted_count'] for u in units)
    blind = sum(u['completed_blind_count'] for u in units)
    assert admitted == blind == traffic['blind_task_attempts']
    assert all(u['current_admitted_count'] == u['completed_blind_count'] for u in units)
    recent_absent = 0
    outer_matches = []
    for cohort in ('bedtools', 'deseq', 'biopython', 'skbio'):
        for stage in ('provider', 'blind'):
            stem = 'evidence/prdiff-' + cohort + '-' + stage + '-01/'
            summary = read(stem + 'summary.json')
            release = read(stem + 'capacity-release.json')
            assert release['controller_state'] == 'SUCCEEDED' and release['released_utc']
            recent_absent += release['sandbox_ids_independently_absent']
            digest = summary['outer_recovery']['sha256'] if stage == 'provider' else summary['original_outer_archive_sha256']
            job = '/exedev/biotasks21-prdiff-' + cohort + '-' + stage + '-20261018-01'
            matches = [x for x in timing['jobs'] if x['job_id'] == job]
            assert len(matches) == 1
            archives = [a.get('output_archive', {}) for task in matches[0]['tasks'] for a in task['attempts']]
            assert any(a.get('sha256') == digest for a in archives), job
            outer_matches.append({'job': job, 'outer_archive_sha256': digest, 'matches_retained_server_hash': True})
            if stage == 'blind':
                assert summary['attempts'] == len(summary['tasks']) == 3 and summary['trial_exceptions'] == 0
                for task in summary['tasks']:
                    assert task['attempts'] == 1 and task['trial_exception'] is None
                    assert task['agent_episodes'] <= summary['approved_limits']['turns']
                    assert all(n <= summary['approved_limits']['output_tokens_per_response'] for n in task['completion_tokens_by_episode'])
    assert not retention['requires_review']
    assert retention['matched'] + retention['superseded_without_original_receipt'] == retention['manifests']
    assert not timing['active_tasks'] and not timing['unavailable_jobs']
    assert not presence['matching_current_sandboxes'] and not presence['active_capacity_claim_files'] and not presence['controller_active_tasks']
    assert budget['accounted_estimates_and_holds_usd'] <= budget['ceiling_usd']
    scope_path = 'evidence/completion-audit-20261017/issue-scope.md'
    report_path = 'comparison-draft.md'
    for name in (scope_path, report_path):
        sources[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    requirements = [
        ('route_inventory', 'assessed', '23 implemented methods, 68 panel/cohort entries; planned unimplemented method excluded.'),
        ('applicable_repository_routes', 'bounded_pass_concluded_with_partial_and_blocked_profiles', '29 units with retained generation records; unsupported/model/backend/input blockers are distinct. No assertion that every supported route reached three tasks.'),
        ('candidate_targets_and_caps', 'historical_protocol_deviations_documented', 'Prelaunch total N is not demonstrated. Several searches are partial. CodeInstruct counts are unknown and each allowance conservatively consumed; no cap reset.'),
        ('independent_acceptance', 'decisions_recorded', '20 tasks admitted under typed reward profiles; rejected, unportable and inconclusive exports excluded. Similarity admission is not correctness admission.'),
        ('every_accepted_task_one_blind_attempt', 'met', f'{admitted} admitted / {blind} single blind attempts; no trial exceptions.'),
        ('seed_routes', 'bounded_pass_concluded_with_failures_and_missing_inputs', 'SCALER admitted as one synthetic family; other designs, invalid answers, timeouts, unattempted seeds and missing recording terms retained separately.'),
        ('marin_reward_and_runtime_compatibility', 'representative_comparison_complete_admission_not_established', 'Six source examples/four structures/27 case pairs. SCALER reward metadata unresolved; exact later runtimes/public images not certified. Zero Atlas admissions.'),
        ('artifact_retention', 'publication_history_reconciled_with_capture_limits', f"{retention['manifests']} manifests/{retention['matched']} matching receipts/one explicit supersession; historical missing output remains missing."),
        ('full_funnel_usage_and_worker_time', 'available_evidence_reconciled_full_observability_not_met', 'Per-unit funnel and61 traffic stages retained; six capture gaps, incomplete worker lifetimes and unverified billing prohibit complete campaign totals.'),
        ('final_conclusions_and_issue_closure', 'report_ready_publication_pending', 'Comparison gives expansion/adaptation/rejection conclusions. Permanent research branch remains unmerged. Closure receipt is recorded separately.')]
    publication_path = 'evidence/final-publication-20261018/receipt.json'
    publication = read(publication_path) if (ROOT / publication_path).exists() else None
    closed = bool(publication and publication.get('issue_state') == 'CLOSED' and publication.get('exact_comment_verified'))
    if closed:
        requirements[-1] = ('final_conclusions_and_issue_closure', 'published_and_closed', publication['comment_url'])
    return {
        'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'objective': 'finish #21', 'research_findings_concluded': True,
        'completion_proven': closed, 'full_original_protocol_compliance_proven': False,
        'completion_basis': 'Bounded feasibility experiment permits negative and inconclusive conclusions. Historical unmet protocol/capture conditions are explicit limitations, not retroactively satisfied requirements.',
        'requirements': [{'requirement': name, 'status': status, 'finding': finding} for name, status, finding in requirements],
        'admitted_tasks': admitted, 'completed_single_blind_attempts': blind,
        'recent_exact_sandboxes_independently_absent': recent_absent,
        'outer_archive_server_hash_checks': outer_matches,
        'source_sha256': sources, 'active_or_submitted_runs': [],
        'completed_output_recovery_pending': [],
        'deferred_integrity_diagnostic': 'unexecuted',
        'new_compute_or_model_calls_required_for_closeout': False,
        'unavailable_evidence': traffic['observability_gaps'] + [
            {'event': 'execution_plan', 'gap': 'Aggregate total N frozen before launch not demonstrated.'},
            {'event': 'provider_accounting', 'gap': 'Separate complete worker lifetimes, invoices and account credit balances unavailable.'}],
    }


if __name__ == '__main__':
    result = build()
    folder = ROOT / 'evidence/completion-audit-20261018'
    folder.mkdir(exist_ok=True)
    (folder / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('research_findings_concluded', 'completion_proven', 'full_original_protocol_compliance_proven', 'admitted_tasks', 'completed_single_blind_attempts', 'recent_exact_sandboxes_independently_absent')}))
