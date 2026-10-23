"""Verify final lifecycle evidence and report scientific acceptance separately."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = 'biotasks34-macs-742-confirm-001'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matching_dependencies(receipts):
    if len(receipts) != 2:
        return False
    identities = []
    for record in receipts:
        receipt = record['receipt']
        wheels = sorted((w['filename'], w['name'], w['version'], w['sha256'], w['bytes']) for w in receipt['wheels'])
        if not wheels:
            return False
        identities.append((receipt['python'], receipt['platform'], wheels))
    return identities[0] == identities[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', required=True, type=Path)
    args = parser.parse_args()
    source = args.experiment.resolve()
    files = {
        'accounting': source/'confirmation-accounting.json',
        'readback': source/'confirmation-readback.json',
        'hf_receipt': ROOT/'confirmation-evidence-receipt.json',
        'cleanup_accounting': source/'confirmation-cleanup-accounting.json',
        'cleanup_readback': source/'confirmation-cleanup-readback.json',
        'journal': ROOT/'private/confirmation-controller/journal.json',
        'budget': ROOT/'budget.json',
        'restart': ROOT/'confirmation-restart-proof.json',
    }
    values = {name:json.loads(path.read_text()) for name,path in files.items()}
    journal = values['journal']
    expected_stages = ['inputs_verified', 'submission_recorded', 'remote_terminal', 'archive_readback_verified',
        'public_eligibility_reviewed', 'hf_readback_verified', 'cleanup_terminal', 'cleanup_verified']
    assert journal['run_id'] == RUN and [r['stage'] for r in journal['stages']] == expected_stages
    assert 'intent' not in journal
    for stage in journal['stages']:
        for item in stage['evidence']:
            assert digest(Path(item['path'])) == item['sha256']
    result = values['readback']
    assert result['run_id'] == RUN and result['model_calls'] == result['task_repairs'] == 0
    assert values['accounting']['attempts'] == values['cleanup_accounting']['attempts'] == 1
    assert result['archive_sha256'] == values['accounting']['output_archive']['sha256']
    receipt = values['hf_receipt']
    assert receipt['anonymous_download_verified'] and receipt['overwrites'] is False
    assert any(r['sha256'] == result['archive_sha256'] and r['path'].endswith('/evidence/confirmation.tar.zst') for r in receipt['objects'])
    cleanup = values['cleanup_readback']
    assert cleanup['archive_sha256'] == values['cleanup_accounting']['output_archive']['sha256']
    assert cleanup['result']['verified_empty'] and cleanup['result']['controls']['verified_empty']
    assert cleanup['result']['remaining_images'] == cleanup['result']['remaining_containers'] == []
    restart = values['restart']
    assert restart['same_handle_observed_after_restart'] and restart['new_remote_submissions'] == 0
    assert restart['journal_sha256_before_restart'] == restart['journal_sha256_after_restart']
    assert restart['submission_sha256_before_restart'] == restart['submission_sha256_after_restart']
    dependencies_match = matching_dependencies(result['dependency_receipts'])
    pair = result['pair']
    gates = dict(reconstruction=result['reconstruction_verified'], unchanged_candidate=result['candidate_files_verified'],
        bootstrap_image_bound=result['bootstrap_image_bound'], two_dependency_receipts=result['dependency_preparation_verified'],
        identical_dependencies_both_controls=dependencies_match, positive_pair=pair['positive_control_pair'],
        clean_oracle_command=pair['clean_oracle_command'], all_regressions_pass=pair['all_regression_tests_pass_both'])
    budget = values['budget']
    assert budget['new_model_calls'] == 0 and not budget['new_paid_capacity_allowed']
    summary = dict(run_id=RUN, lifecycle_complete=True, scientific_acceptance=all(gates.values()), gates=gates,
        remote_attempts=1, cleanup_attempts=1, adopted_existing_submission=False,
        live_controller_restart_verified=True, rows=result['rows'],
        dependency_sets=[dict(image_id=r['image_id'], python=r['receipt']['python'],
            platform=r['receipt']['platform'], wheels=r['receipt']['wheels']) for r in result['dependency_receipts']],
        allocated_cpu_hours_this_attempt=values['accounting']['allocated_cpu_hours']+values['cleanup_accounting']['allocated_cpu_hours'],
        cumulative_allocated_cpu_hours=budget['additional_allocated_cpu_hours'], new_model_calls=0,
        hf_prefix=receipt['prefix'], evidence_sha256={name:digest(path) for name,path in files.items()},
        limits=['One separate MACS diagnostic; frozen 83-export cohort counts are unchanged',
            'Mutable bootstrap package sources and future wheel availability remain limitations',
            'No Docker image distribution, solver score or production-pipeline claim',
            'Storage billing remains reserved until authoritative reconciliation'])
    (ROOT/'confirmation-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','dependency_sets','evidence_sha256','limits')}))


if __name__ == '__main__':
    main()
