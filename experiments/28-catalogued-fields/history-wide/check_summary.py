"""Synthetic full-cohort evidence checks; no provider, native test or model execution."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from summarize import sha, summarize


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def main():
    with TemporaryDirectory(prefix='history-summary-check-') as temporary:
        base = Path(temporary); root = base / 'history-wide'
        cohort = [{'repo': 'fixture/' + str(i), 'slug': str(i), 'field_label': 'fixture', 'ref': str(i)} for i in range(10)]
        save(base / 'cohort.json', cohort)
        for row in cohort:
            save(root / 'candidate-identities' / (row['slug'] + '.json'), {'pr_numbers': [2, 1]})
        initial = summarize(root)
        assert not initial['all_ten_result_evidence_complete']
        assert all(r['primary_verified'] is None and r['actual_cost_usd'] is None and r['native_backlog'] is None for r in initial['repositories'])
        base_trial = {'reward': 0, 'reward_consistent': True, 'original_grade_matches_raw_log': True,
            'exact_pinned_verifier': True, 'task_files_unchanged': True,
            'reward_details': {'parse_status': 'ok', 'command_resolved': False}}
        oracle_trial = deepcopy(base_trial); oracle_trial['reward'] = 1
        task = {'task': 'fixture', 'raw_primary_verified': True, 'strict_clean_verified': False,
            'also_exported_in_september_baseline': True,
            'controls': {'nop': base_trial, 'oracle': oracle_trial}}
        for row in cohort:
            slug = row['slug']; good = slug == '0'
            result = {'repo': row['repo'], 'ref': row['ref'], 'frozen_history_identities': 2,
                'coverage': {'complete_identity_accounting': True, 'native_entered_pr_numbers': [2],
                    'native_discovery_omitted_pr_numbers': [], 'backlog_count': 1,
                    'native_unique_returned_count': 2, 'native_returned_appearances': 2, 'native_list_available': True,
                    'batches': [{'paired_started': int(good), 'validation_result_files': int(good), 'entered_without_native_decision': []}]},
                'task_controls': [deepcopy(task)] if good else [], 'raw_primary_verified_tasks': int(good),
                'raw_strict_clean_verified_tasks': 0, 'native_exports_manifest_present': int(good),
                'original_phase_sha256': 'fixture-phase', 'billing': {'cost_complete': True,
                    'unresolved_calls': [], 'actual_cost_usd': '1'}, 'allocated_cpu_hours': '2',
                'original_control_allocation': [{'command': ['fixture']}] if good else [],
                'wrapper_state': 'SUCCEEDED', 'native_parent_state': 'bounded_with_backlog',
                'native_parent_stop_reason': 'fixture', 'native_skip_reasons': {}, 'native_error_reasons': {},
                'owned_cleanup_empty': True}
            result_path = root / 'results' / (slug + '.json'); save(result_path, result)
            manifest = root / 'archives' / (slug + '-manifest.json')
            save(manifest, {'files': [{'path': 'evidence/phase-artifacts.tar.gz', 'sha256': 'fixture-phase'}]})
            save(root / 'archives' / (slug + '-receipt.json'), {'anonymous_download_verified': True, 'manifest_sha256': sha(manifest)})
            save(root / 'accounting' / (slug + '.json'), {'all_ten_accounting_audited': False, 'repositories': [{
                'repo': row['repo'], 'task_byte_audit_in_assessment': sha(result_path),
                'archive_manifest_sha256': sha(manifest), 'original_phase_sha256': 'fixture-phase'}]})
        complete = summarize(root)
        assert complete['all_ten_result_evidence_complete'] and complete['known_terminal_history_cost_usd'] == '10'
        assert complete['cost_per_verified_task_usd'] == '10' and complete['cost_per_successful_repository_usd'] == '10'
        assert complete['strict_clean_tasks_with_accepted_evidence'] == 0
        assert complete['primary_verified_tasks_with_accepted_evidence'] == 1
        assert complete['new_to_baseline_primary_verified_with_accepted_evidence'] == 0
        missing = root / 'results/9.json'; original = missing.read_bytes(); missing.unlink()
        partial = summarize(root)
        assert not partial['all_ten_result_evidence_complete'] and partial['cost_per_verified_task_usd'] is None
        assert partial['repositories'][9]['exports'] is None and partial['active_and_unreported_costs_excluded']
        missing.write_bytes(original)
        result_path = root / 'results/0.json'; value = json.loads(result_path.read_text())
        value['task_controls'][0]['controls']['oracle']['exception'] = 'VerifierTimeoutError'
        save(result_path, value)
        try:
            summarize(root)
        except AssertionError:
            pass
        else:
            raise AssertionError('Timeout retained a claimed primary verification')
        value['task_controls'][0]['controls']['oracle'].pop('exception')
        value['checked_utc'] = 'fixture-new-assessment'; save(result_path, value)
        stale = summarize(root)
        assert not stale['all_ten_result_evidence_complete'] and not stale['repositories'][0]['accounting_accepted']
    print('History summary fixtures passed: all ten rows, missing != zero, failed-repo cost inclusion, full evidence before ratios, source/manifest identity, stale assessment audit rejection, timeout grade unavailability, tracked versus clean success and baseline-overlap separation. No model/API/native test execution; scratch removed.')


if __name__ == '__main__':
    main()
