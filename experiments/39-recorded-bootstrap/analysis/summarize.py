"""Separate fresh outcomes, native baseline and lifecycle claims."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import sha,write
from preserve import verified_receipt


def main():
    directory=ROOT/'private/OHIF__Viewers';read=json.loads((directory/'readback.json').read_text())
    account=json.loads((directory/'accounting.json').read_text());hf=verified_receipt(directory)
    complete=json.loads((directory/'complete.json').read_text());assert complete['hf_manifest_sha256']==hf['manifest_sha256']
    proof=json.loads((directory/'cleanup-proof.json').read_text());assert proof['cleanup']['verified_empty']
    task=read['tasks'][0];attempted=bool(task['rows']);boot=read.get('bootstrap_replay') or {}
    result=dict(issue=39,task=task['task'],original_task_identity=task['original_task_identity'],candidate_task_identity=task['prepared_task_identity'],
        source_variant='recorded_bootstrap_dependency',baseline_issue=37,baseline='Native inline recipe exited 127: pnpm missing; no controls',
        stage=read['stage'],bootstrap_stage=boot.get('stage'),replay_status=(boot.get('replay') or {}).get('status'),
        replay_steps_attempted=len((boot.get('replay') or {}).get('steps',[])),bootstrap_source_commit=boot.get('source_commit'),
        public_base_image_id=boot.get('base_image_id'),bootstrap_image_id=boot.get('image_id'),
        smoke_passed=boot.get('smoke_passed'),fresh_image_check_passed=boot.get('verify_passed'),fresh_image_check_detail=boot.get('verify_detail'),
        control_invocations=read['control_invocations_started'],rows=task['rows'],
        positive_control_pair=task['positive_control_pair'] if attempted else None,
        clean_oracle_command=task['clean_oracle_command'] if attempted else None,
        all_tracked_p2p_pass_both=task['all_p2p_pass_both'] if attempted else None,
        images=read['image_identities'],allocated_cpu_hours=account['allocated_cpu_hours'],attempts=account['attempts'],model_calls=0,
        raw_archive_sha256=read['archive_sha256'],hf_prefix=hf['prefix'],anonymous_download_verified=True,cleanup_verified=True,
        initializer_required=True,task_dockerfile_alone_standalone=False,image_pushed=False,new_unique_tasks=0,historical_cohort_totals_unchanged=True)
    write(ROOT/'results.json',result)
    lines=['# Recorded-bootstrap comparison','',f"OHIF #5996: stage `{result['stage']}`, bootstrap `{result['bootstrap_stage']}`, replay `{result['replay_status']}` ({result['replay_steps_attempted']} steps attempted).",'',
        'The sealed #37 native-inline baseline failed at missing pnpm before controls. This is a different declared environment reconstruction variant; original grading assets, per-task overlay, resource contract and verifier timeout are unchanged.','',
        '| Control | Reward | F2P passed/total | P2P passed/total | Whole command exit | Untracked failures |','| --- | --- | --- | --- | --- | --- |']
    for row in task['rows']:
        lines.append('| '+ ' | '.join(str(v) for v in [row['agent'],row['native_reward'],f"{row['f2p_passed']}/{row['f2p_total']}",f"{row['p2p_passed']}/{row['p2p_total']}",row['test_exit_code'],row['untracked_failed_count']])+' |')
    if not attempted:lines.append('| Neither attempted | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |')
    lines += ['',f"Positive pair: `{result['positive_control_pair']}`; clean full oracle command: `{result['clean_oracle_command']}`. One terminal attempt used {result['allocated_cpu_hours']:.6f} allocated CPU-hours, zero model calls. Raw archive/readback and owned cleanup are verified.",'',
        'The portable input bundle is available after cleanup, with verified anonymous download before this run. Rebuilding it requires the explicit initializer, original public Git/base images and dependency services; the task Dockerfile alone is not standalone. No installed image/layers or dependency tree was published. One replay is not a cohort-wide reproducibility or cross-time byte-identity result.','',f"Runtime archive: `hf://buckets/open-athena/biotasks/{hf['prefix']}`.",'']
    (ROOT/'results.md').write_text('\n'.join(lines))
    records=ROOT/'runs/OHIF__Viewers';records.mkdir(parents=True,exist_ok=True)
    for name in ['journal.json','submission.json','accounting.json','readback.json','manifest.json','hf-receipt.json','cleanup-proof.json','complete.json','admission.json','candidate.json','preflight.json']:
        shutil.copyfile(directory/name,records/name)
    print(json.dumps({k:result[k] for k in ['stage','bootstrap_stage','replay_status','control_invocations','positive_control_pair','clean_oracle_command','allocated_cpu_hours']}))


if __name__=='__main__':main()
