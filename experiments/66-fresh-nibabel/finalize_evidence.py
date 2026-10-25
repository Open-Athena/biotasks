"""Record source-bound completed evidence; no transport or execution admission."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
work = root / 'inputs-private/run-001'
result = json.loads((root / 'inputs-private/controller-output.log').read_text())
assert result['state'] == 'workflow_complete'
outcomes = result['results'][0]['control_outcomes']
assert outcomes['eligible_bundle_instances'] == 1 and not outcomes['unsupported']
validation = work / 'nibabel-handoff/validation'
plan = json.loads((validation / 'plan.json').read_text())
assert len(plan['tasks']) == 1
control = validation / 'runs' / plan['tasks'][0]['id']
generation = work / 'nibabel/runs/generation'
publications = []
allocation = {}
stages = ['candidate_verified', 'submission_recorded', 'remote_terminal', 'archive_readback_verified', 'publication_resolved', 'cleanup_terminal', 'cleanup_verified']
for kind, directory in [('generation', generation), ('control', control)]:
    journal = json.loads((directory / 'journal.json').read_text())
    assert [s['stage'] for s in journal['stages']] == stages and not journal.get('intent')
    cleanup = json.loads((directory / 'cleanup-proof.json').read_text())
    assert cleanup['verified_empty'] and all(not v for v in cleanup['remaining'].values())
    assert cleanup['protected_public_base']['preserved']
    shutil.copyfile(directory / 'cleanup-proof.json', root / f'{kind}-cleanup-proof.json')
    for role, subdirectory in [('primary', directory), ('cleanup', directory / 'cleanup')]:
        receipt = json.loads((subdirectory / 'publication.json').read_text())
        assert receipt['anonymous_download_verified']
        publications.append({'kind': kind, 'role': role, 'prefix': receipt['prefix'], 'anonymous_readback_verified': True})
        allocation[f'{kind}_{role}'] = json.loads((subdirectory / 'accounting.json').read_text())['allocated_cpu_hours']
        for src, dest in [('preserved/manifest.json', f'{kind}-{role}-manifest.json'), ('publication.json', f'{kind}-{role}-hf-receipt.json')]:
            shutil.copyfile(subdirectory / src, root / dest)
readback = json.loads((control / 'readback.json').read_text())
assert all(readback[k] for k in ['complete_parseable_pair', 'positive_control_pair', 'clean_oracle_command', 'all_p2p_pass_both'])
by_agent = {row['agent']: row for row in readback['controls']}
assert by_agent['nop']['native_reward'] == 0 and by_agent['oracle']['native_reward'] == 1
assert by_agent['nop']['f2p_passed'] == 0 and by_agent['oracle']['f2p_passed'] == 9
assert all(x['p2p_passed'] == x['p2p_total'] == 37 and x['untracked_failed_count'] == 0 for x in by_agent.values())
assert by_agent['oracle']['exit_code'] == 0 and by_agent['nop']['exit_code'] == 1
budget_path = Path(json.loads((root / 'manifest.json').read_text())['budget_ledger'])
budget_bytes = budget_path.read_bytes()
budget = json.loads(budget_bytes)
assert budget['outstanding_cpu_hour_reservations'] == 0 and not budget['paid_model_execution_enabled']
model_rows = [x for x in budget['events'] if x['kind'] == 'model_run_reservation']
assert all(x['state'] == 'terminal reconciled' and float(x['outstanding_usd']) == 0 for x in model_rows)
assert budget['recorded_paid_cost_usd'] + budget['outstanding_reservations_usd'] < 90
assert budget['additional_allocated_cpu_hours'] < 32
proof = json.loads((root / 'completed-replay-proof.json').read_text())
assert proof['completed_replay_byte_inert'] and proof['transport_and_credential_reads_forbidden']
assert proof['budget_sha256'] == hashlib.sha256(budget_bytes).hexdigest()
summary = dict(
    state='workflow_complete', original_controller_session=20607, original_controller_exit=0,
    fresh_generation_runs=1, native_control_workflows=1, native_control_sides=2,
    task='nipy__nibabel-1574', task_source_identity=outcomes['tasks'][0]['source_identity'],
    f2p_total=9, nop_f2p_passed=0, oracle_f2p_passed=9, p2p_passed_both=37,
    nop_reward=0, oracle_reward=1, nop_exit=1, oracle_exit=0, untracked_failures_both=0,
    tracked_positive_pair=True, eligible_for_this_control_profile=True,
    selected_test_scope='nibabel/tests/test_parrec.py', whole_repository_test_suite_verified=False,
    input_origin='Packaged phantom header fixtures adapted in memory by the original PR; no new observed biological samples; acquisition/simulation provenance not independently established',
    dataset_release=False, model_calls=13, model_actual_usd='0.473580', task_repairs=0,
    allocation_cpu_hours=allocation, total_allocated_cpu_hours=sum(allocation.values()),
    all_four_hf_anonymous_readbacks_verified=True, publications=publications,
    owned_resources_empty=True, protected_public_base_preserved=True,
    completed_actual_installed_cli_replay_byte_inert=True,
    epic_budget={k: budget[k] for k in ['additional_allocated_cpu_hours', 'outstanding_cpu_hour_reservations', 'recorded_paid_cost_usd', 'outstanding_reservations_usd', 'new_model_calls', 'paid_model_execution_enabled']},
    budget_sha256=proof['budget_sha256'],
)
for name, value in [('final-summary.json', summary), ('controller-result.json', result), ('control-outcomes.json', outcomes)]:
    (root / name).write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(summary, indent=2))
