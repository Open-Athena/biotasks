"""Compare source-bound reference results; guard a completed native reinvocation."""
from pathlib import Path

from biotasks.validation import bridge, controller, preservation
from biotasks.validation.files import inventory, read_json, sha, write_json
from biotasks.validation.journal import STAGES

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'runs-private/native-001'


def main():
    plan=read_json(RUN/'plan.json')
    references=read_json(ROOT/'reference-inputs.json')['references']
    rows=[]
    for group,ref in zip(plan['tasks'],references,strict=True):
        directory=RUN/'runs'/group['id']
        journal=read_json(directory/'journal.json')
        assert [r['stage'] for r in journal['stages']]==list(STAGES), 'Native workflow not complete'
        current=read_json(directory/'readback.json')
        preservation.verify_receipt(directory)
        preservation.verify_receipt(directory/'cleanup')
        proof=read_json(directory/'cleanup-proof.json')
        assert proof['verified_empty'] and not any(proof.get('remaining',{}).values())
        expected_files={r['path'].split('/'+ref['task']+'/',1)[1]:(r['sha256'],r['mode']) for r in ref['source_files']}
        actual_files={r['path'].removeprefix(group['task']['relative_directory']+'/'):(r['sha256'],r['mode']) for r in group['task']['files']}
        assert actual_files==expected_files
        expected=ref['expected_baseline']
        expected_sides={r['agent']:r for r in expected.get('rows',[])}
        comparable=[]
        for c in current['controls']:
            old=expected_sides[c['agent']]
            keys=['native_reward','parse_status','resolved','command_resolved','f2p_passed','f2p_total','p2p_passed','p2p_total','untracked_failed_count']
            comparable.append(dict(agent=c['agent'],same_native_fields=all(c[k]==old[k] for k in keys),same_test_command_exit=c['exit_code']==old['test_exit_code']))
        positive_expected=expected.get('positive_control_pair',False)
        clean_expected=expected.get('clean_oracle_command',False)
        same_flags=current['positive_control_pair']==positive_expected and current['clean_oracle_command']==clean_expected
        stage_expected='controls_returned' if positive_expected else 'bootstrap_build_failed'
        same_stage=current['stage']==stage_expected
        receipts=[read_json(directory/'publication.json'),read_json(directory/'cleanup/publication.json')]
        allocations=[read_json(directory/'accounting.json')['allocated_cpu_hours']]
        if (directory/'cleanup/accounting.json').exists():allocations.append(read_json(directory/'cleanup/accounting.json')['allocated_cpu_hours'])
        rows.append(dict(task=ref['task'],task_file_bytes_modes_unchanged=len(actual_files),eight_original_grading_assets_unchanged=True,source_identity=group['task']['source_identity'],current_stage=current['stage'],same_expected_stage=same_stage,positive_control_pair=current['positive_control_pair'],clean_oracle_command=current['clean_oracle_command'],same_expected_flags=same_flags,control_comparisons=comparable,all_native_fields_match=all(c['same_native_fields'] and c['same_test_command_exit'] for c in comparable),cleanup_verified=True,protected_public_base=proof.get('protected_public_base'),hf_snapshots=[r['prefix'] for r in receipts],anonymous_readbacks_verified=all(r['anonymous_download_verified'] for r in receipts),actual_allocated_cpu_hours=sum(allocations)))
    # This is a genuine completed native run, guarded against *any* transport
    # call during reinvocation, not a mocked native execution.
    before=inventory(RUN)
    ledger=Path(plan['budget_ledger'])
    budget_before=sha(ledger)
    def forbidden(*args,**kwargs):raise AssertionError('Completed native reinvocation attempted transport')
    bridge.call=forbidden
    result=controller.run(RUN,once=True)
    assert result['state']=='complete'
    assert inventory(RUN)==before and sha(ledger)==budget_before
    value=dict(issue=44,pipeline_commit='cb3d2b78',plan_identity=plan['plan_identity'],comparisons=rows,all_expected_results_match=all(r['same_expected_stage'] and r['same_expected_flags'] and r['all_native_fields_match'] for r in rows),completed_native_reinvoke=dict(state=result['state'],transport_forbidden=True,run_files_before_after=len(before),run_files_unchanged=True,epic_budget_unchanged=True),new_model_calls=0,new_capacity=False,task_repairs=0,scope='Two existing reference exports; neither new generation, cohort portability nor grader robustness',known_controller_limitation='Watch mode waits five minutes after a recovered effect even when that effect has produced ready evidence. No additional native compute is consumed, but serial wall time is unnecessarily long.')
    write_json(ROOT/'native-comparison.json',value)
    print({k:value[k] for k in ['all_expected_results_match','completed_native_reinvoke','new_model_calls']})


if __name__=='__main__':main()
