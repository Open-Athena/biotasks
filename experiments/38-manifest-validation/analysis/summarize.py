"""Post-run evidence table; does not alter the frozen controller or rewards."""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import sha,write
from evidence import archive_records
from preserve import inspect,verified_receipt
from resume_runner import STAGES


def main():
    cohort=json.loads((ROOT/'cohort.json').read_text());plan=json.loads((ROOT/'runtime-plan.json').read_text())
    assert sha(ROOT/'cohort.json')==plan['cohort_sha256']
    rows=[];families=[];records=[];observations=[]
    for filename in ['controller-second.log','controller-third.log']:
        for line in (ROOT/'private'/filename).read_text().splitlines():
            if line.startswith('{"observed":'):observations.append(json.loads(line))
    for config in plan['families']:
        source=next(f for f in cohort['families'] if f['id']==config['id'])
        if config['mode']=='reference_stop':
            rows.extend(dict(repo=source['repo'],task=t['task'],source_variant='lookup_candidate',
                state='not_attempted_shared_prerequisite_stop',job_id=None,
                original_task_identity=t['original_task_identity'],prepared_task_identity=t['prepared_task_identity'],
                control_invocations=0,complete_pair=None,positive_pair=None,clean_oracle_command=None,
                reference_issue=37,reference_measured_task=source['imported_failure']['measured_task']) for t in source['tasks'])
            continue
        directory=ROOT/'private'/config['id'];result=json.loads((directory/'readback.json').read_text())
        account=json.loads((directory/'accounting.json').read_text());journal=json.loads((directory/'journal.json').read_text())
        assert [s['stage'] for s in journal['stages']]==list(STAGES) and 'intent' not in journal
        assert account['attempts']==1 and account['exit_code']==0 and result['input_package_verified'] and result['task_package_verified']
        assert result['original_images_absent'] and result['model_calls']==result['task_repairs']==0
        proof=json.loads((directory/'cleanup-proof.json').read_text());assert proof['route']=='primary' and proof['cleanup']['verified_empty']
        receipt=verified_receipt(directory)
        target=ROOT/'runs'/config['id'];target.mkdir(parents=True,exist_ok=True)
        for name in ['journal.json','submission.json','accounting.json','readback.json','manifest.json','hf-receipt.json',
            'cleanup-proof.json','complete.json','admission.json','candidate.json','preflight.json']:
            data=(directory/name).read_bytes();inspect(data)
            if (target/name).exists():assert (target/name).read_bytes()==data
            else:shutil.copyfile(directory/name,target/name)
            records.append(dict(path=str((target/name).relative_to(ROOT)),bytes=len(data),sha256=sha(target/name)))
        for t in result['tasks']:
            oracle=next((r for r in t['rows'] if r['agent']=='oracle'),{})
            invoked=sum(r['state']!='unstarted' for r in t['rows'])
            rows.append(dict(repo=result['repo'],task=t['task'],source_variant=result['source_variant'],state=t['state'],
                job_id=account['job_id'],original_task_identity=t['original_task_identity'],prepared_task_identity=t['prepared_task_identity'],
                control_invocations=invoked,complete_pair=t['complete_parseable_pair'] if invoked else None,
                positive_pair=t['positive_control_pair'] if invoked else None,clean_oracle_command=t['clean_oracle_command'] if invoked else None,
                all_p2p_pass_both=t['all_p2p_pass_both'] if invoked else None,oracle_test_exit=oracle.get('test_exit_code'),
                oracle_untracked_failed=oracle.get('untracked_failed_count'),image_identity_captures=t['image_identity_captures']))
        families.append(dict(id=config['id'],job_id=account['job_id'],stage=result['stage'],attempts=account['attempts'],
            allocated_cpu_hours=account['allocated_cpu_hours'],worker_id=result['worker_id'],hf_prefix=receipt['prefix'],
            hf_objects=len(receipt['objects']),cleanup_verified=True,bootstrap_build_exit=result['bootstrap_build_exit']))
    assert len(rows)==25 and len({r['task'] for r in rows})==25
    before=json.loads((ROOT/'restart-before.json').read_text());after=json.loads((ROOT/'restart-after.json').read_text())
    assert before['job_id']==after['job_id']==families[0]['job_id'] and before['submission_sha256']==after['submission_sha256']
    assert sha(ROOT/'private'/families[0]['id']/'submission.json')==before['submission_sha256']
    reinvoke=json.loads((ROOT/'completed-reinvoke.json').read_text());assert reinvoke['all_journals_submissions_accounts_receipts_and_budget_unchanged']
    cleanups=[o['observed'] for o in observations if o.get('family')==families[0]['id'] and o['state']=='cleanup_verified']
    next_submit=[o['observed'] for o in observations if o.get('family')==families[1]['id'] and o['state']=='performed:submission_recorded']
    assert len(cleanups)==len(next_submit)==1 and cleanups[0]<next_submit[0]
    write(ROOT/'controller-observations.json',observations)
    summary=dict(issue=38,lifecycle_complete=True,public_tasks=25,native_tasks=13,lookup_candidate_reference_tasks=12,
        control_invocations=sum(r['control_invocations'] for r in rows),complete_pairs=sum(r['complete_pair'] is True for r in rows),
        positive_pairs=sum(r['positive_pair'] is True for r in rows),clean_oracle_commands=sum(r['clean_oracle_command'] is True for r in rows),
        historical_cohort_totals_unchanged=dict(exports=83,ever_positive=82,ever_clean=67),new_unique_tasks=0,
        allocated_cpu_hours=sum(f['allocated_cpu_hours'] for f in families),families=families,
        identical_worker_code_across_native_families=all(f['payload_manifest']['worker_code_sha256']==plan['worker_code_sha256'] for f in plan['families'] if f['mode']=='native_inline'),
        real_controller_restart_same_handle=True,terminal_attempts_one_each=True,completed_reinvocation_unchanged=True,
        serial_archive_cleanup_before_next_submission=True,all_primary_cleanup_verified=True,
        model_calls=0,new_capacity=False,recorded_paid_cost_usd=0,existing_storage_reservation_unreconciled_usd=10,
        pre_submission_controller_failure_preserved='pre-submission-failure.json',records=records,tasks=rows,
        limits=['Native positive pairs retain original grading; ten oracle commands have additional untracked failures',
            'Scanpy stopped at a prerequisite build failure; no controls or task reward',
            'Twelve OHIF lookup candidates not attempted; one earlier failure is imported, not twelve measured failures',
            'No new generation yield, solver evaluation, image byte identity or production-readiness claim',
            'Archive/transport failure recovery has offline checks; no live failure was injected'])
    write(ROOT/'results.json',summary)
    lines=['# Frozen-export validation results','',
        'One frozen controller completed both native families through verified public archival and primary cleanup. A deliberate watcher restart retained the same handle; terminal accounting shows one attempt per family. Completed reinvocation left journals, submissions, accounts, receipts and budget byte-identical. The initial receipt-schema failure was before submission and is preserved separately.','',
        '| Source family | New control pairs | Native positive pairs | Clean oracle commands | Outcome |',
        '| --- | ---: | ---: | ---: | --- |',
        '| Cobrapy, native inline | 12 | 12 | 2 | All tracked F2P repaired and P2P preserved; ten oracle commands also report untracked failures |',
        '| Scanpy, native inline | 0 | — | — | Common build exit 100: apt cannot locate required packages; controls not attempted |',
        '| OHIF, lookup candidate | 0 | — | — | Twelve cases not attempted under sealed shared-prerequisite stop; #37 is one measured build failure |','',
        'Original grading and 300-second/one-CPU/6-GiB task settings remain unchanged. Native positive reward and clean full oracle command are separate findings. No task source, install command, test or oracle was repaired.','',
        f'Experiment allocation: {summary["allocated_cpu_hours"]:.9f} CPU-hours, two existing reserved jobs, zero model calls/new capacity. Both emergency cleanup reservations were released unused. Storage billing remains unreconciled under the existing $10 reservation. Original 83/82/67 historical totals remain unchanged.','',
        '| Task | Variant | State | Pair | Positive | Clean oracle | Oracle exit | Untracked failures |',
        '| --- | --- | --- | --- | --- | --- | ---: | ---: |']
    def mark(value):return '—' if value is None else 'yes' if value else 'no'
    def number(value):return '—' if value is None else str(value)
    for r in rows:
        lines.append('| '+ ' | '.join([r['task'],r['source_variant'],r['state'],mark(r['complete_pair']),mark(r['positive_pair']),mark(r['clean_oracle_command']),number(r.get('oracle_test_exit')),number(r.get('oracle_untracked_failed'))])+' |')
    (ROOT/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:summary[k] for k in ['lifecycle_complete','control_invocations','complete_pairs','positive_pairs','clean_oracle_commands','allocated_cpu_hours']}))


if __name__=='__main__':main()
