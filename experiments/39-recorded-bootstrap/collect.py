"""Derive task outcomes from native trial/reward bytes, never job success alone."""
import json
from pathlib import Path
import subprocess

from common import content_sha,json_sha,safe,sha,write
from evidence import archive_records

ROOT=Path(__file__).resolve().parent


def download(account,directory,gcloud='/home/exedev/.local/google-cloud-sdk/bin/gcloud'):
    output=account['output_archive'];assert output['state']=='uploaded' and output['size_bytes']<32*1024**2
    run=account['job_id'].removeprefix('/exedev/')
    assert output['uri'].startswith('gs://') and '/task-outputs/exedev/'+run+'/' in output['uri']
    dest=Path(directory)/'output';dest.mkdir(exist_ok=True);archive=dest/'outputs.tar.zst'
    if not archive.exists():
        pending=dest/'download.partial'
        pending.unlink(missing_ok=True)
        subprocess.run([gcloud,'storage','cp','--quiet',output['uri'],str(pending)],check=True,capture_output=True,timeout=180)
        assert pending.stat().st_size==output['size_bytes'] and sha(pending)==output['sha256']
        pending.rename(archive)
    assert archive.stat().st_size==output['size_bytes'] and sha(archive)==output['sha256']
    return archive


def cleanup_readback(family,directory):
    directory=Path(directory);account=json.loads((directory/'accounting.json').read_text())
    assert account['job_id']=='/exedev/'+family['run_id'] and account['attempts']==1
    archive=download(account,directory);outer=archive_records(archive,'tar.zst')
    envelope=json.loads(outer['cleanup-envelope.json']['data']);result=json.loads(outer['cleanup-result.json']['data'])
    source=json.loads((directory/'submission.json').read_text())
    assert envelope['primary_run_id']==result['run_id']==family['primary_run_id']
    expected={k:v for k,v in family['payload_sha256'].items() if k!='cleanup-payload.json'}
    assert envelope['payload_sha256']==expected
    assert envelope['worker_id']==source['worker_id']==family['cleanup_target']['worker_id']
    assert envelope['cleanup_result_sha256']==outer['cleanup-result.json']['sha256']
    assert envelope['downloaded_tools_removed'] and result['verified_empty'] and not any(result['remaining'].values())
    value=dict(run_id=family['run_id'],primary_run_id=family['primary_run_id'],cleanup=result,
        archive_sha256=sha(archive),worker_id=envelope['worker_id'],payload_verified=True,model_calls=0)
    write(directory/'readback.json',value);return value


def parse_control(control,task,packed):
    assert control['task']==task['task'] and control['agent'] in ('nop','oracle')
    assert control['verifier_timeout_seconds']==300
    prefix='jobs/'+task['task']+'/'
    trials=control.get('trial_results',[]);assert len(trials)<=1
    trial=trials[0]['result'] if trials else {}
    for item in trials:assert json.loads(packed[prefix+item['path']]['data'])==item['result']
    for name,text in control.get('reward_files',{}).items():assert packed[prefix+name]['data'].decode()==text
    details=[json.loads(text) for name,text in control.get('reward_files',{}).items() if name.endswith('/reward-details.json')]
    assert len(details)<=1;detail=details[0] if details else {}
    reward=((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    if details:assert reward==detail['reward']
    logs=[dict(path=name,bytes=row['bytes'],sha256=row['sha256']) for name,row in packed.items()
        if name.startswith(prefix+control['name']+'/') and name.endswith('/verifier/test-stdout.txt')]
    assert len(logs)<=1
    return dict(agent=control['agent'],state=control['state'],wrapper_exit=control.get('exit_code'),
        trial_present=bool(trial),reward_details_present=bool(details),exception=trial.get('exception_info'),
        native_reward=reward,parse_status=detail.get('parse_status'),resolved=detail.get('resolved'),
        command_resolved=detail.get('command_resolved'),test_exit_code=detail.get('exit_code'),
        f2p_passed=detail.get('f2p_passed'),f2p_total=detail.get('f2p_total'),
        p2p_passed=detail.get('p2p_passed'),p2p_total=detail.get('p2p_total'),
        untracked_failed_count=detail.get('untracked_failed_count'),raw_test_logs=logs)


def pair_flags(rows,task):
    sides={r['agent']:r for r in rows};assert len(sides)==len(rows)
    complete=(set(sides)=={'nop','oracle'} and all(r['state']=='completed' and r['wrapper_exit']==0 and
        r['trial_present'] and r['reward_details_present'] and not r['exception'] and r['parse_status']=='ok' and
        r['f2p_total']==task['expected_f2p'] and r['p2p_total']==task['expected_p2p'] and len(r['raw_test_logs'])==1
        for r in sides.values()))
    positive=bool(complete and sides['nop']['native_reward']==0 and sides['oracle']['native_reward']==1 and sides['oracle']['resolved'] is True)
    clean=bool(complete and sides['oracle']['command_resolved'] is True and sides['oracle']['test_exit_code']==0)
    regression=bool(complete and all(r['p2p_passed']==r['p2p_total'] for r in sides.values()))
    return dict(complete_parseable_pair=complete,positive_control_pair=positive,clean_oracle_command=clean,all_p2p_pass_both=regression)


def readback(family,directory,gcloud='/home/exedev/.local/google-cloud-sdk/bin/gcloud'):
    directory=Path(directory);account=json.loads((directory/'accounting.json').read_text())
    assert account['job_id']=='/exedev/'+family['run_id'] and account['attempts']==1
    archive=download(account,directory,gcloud)
    outer=archive_records(archive,'tar.zst')
    report_row=outer.get('result.json') or outer.get('work-state.json')
    assert report_row, 'No source-bound report: preserve archive, never invent identity/cleanup'
    report=json.loads(report_row['data'])
    assert report['run_id']==family['run_id'] and report['payload_sha256']==family['payload_manifest']['sha256']
    submission=json.loads((directory/'submission.json').read_text())
    assert report['worker_id']==submission['worker_id'] and report['different_worker_verified']
    for name,digest in report.get('output_sha256',{}).items():assert outer[str(safe(name))]['sha256']==digest
    config=json.loads((ROOT/family['payload_directory']/'family.json').read_text())
    absence=report.get('original_image_absence')=={ref:True for ref in config['original_image_refs']}
    input_verified=False
    if 'input-package.tar.gz' in outer:
        assert outer['input-package.tar.gz']['sha256']==config['task_bundle']['sha256']
        input_verified=True
    tasks=config['tasks'];packed={};recipes_verified=False
    if 'control-artifacts.tar.gz' in outer:
        packed=archive_records(outer['control-artifacts.tar.gz']['data'],'tar.gz')
        expected={r['path']:r for t in tasks for r in t['files']}
        assert {n for n in packed if n.startswith('outputs/')}==set(expected)
        for name,spec in expected.items():
            row=packed[name];assert row['sha256']==spec['sha256'] and row['bytes']==spec['bytes'] and row['mode']==int(spec['mode'],8)
        recipes_verified=True
    builds=[json.loads(line) for line in outer.get('bounded-builds.jsonl',dict(data=b''))['data'].decode().splitlines()]
    identities=[json.loads(line) for line in outer.get('image-identities.jsonl',dict(data=b''))['data'].decode().splitlines()]
    if builds:
        from docker_bridge import tagged_recipe
        assert all(b['kind']=='task' for b in builds)
        expected_prefix=None
        for build in builds:
            if build.get('blocked_by_prior_build_failure'):continue
            raw=expected_prefix if build['kind']=='bootstrap' else packed[next(f['path'] for t in tasks if t['task']==build['task'] for f in t['files'] if f['path'].endswith('/environment/Dockerfile'))]['data']
            assert content_sha(raw)==build['dockerfile_sha256']
            if not build.get('cached'):
                effective=tagged_recipe(raw,family['run_id'])
                assert packed['infra/'+build['dockerfile_sha256']+'.Dockerfile']['data']==effective
                assert content_sha(effective)==build['effective_dockerfile_sha256']
    task_states={r['task']:r for r in report.get('tasks',[])}
    outcomes=[]
    for task in tasks:
        name=task['task'];state=task_states.get(name,dict(state='infrastructure_interrupted'))
        path='controls/'+name+'/controls.json'
        controls=json.loads(outer[path]['data']) if path in outer else []
        rows=[parse_control(row,task,packed) for row in controls]
        flags=pair_flags(rows,task)
        unchanged='controls/'+name+'/task-files-unchanged.json'
        if unchanged in outer:
            verified=json.loads(outer[unchanged]['data']);expected={r['path']:r['sha256'] for r in task['files']}
            assert verified['verified'] and verified['before']==verified['after']==expected
        source_bound=[]
        for identity in [r for r in identities if r['task']==name]:
            assert identity['git_head']==task['base_commit']
            latest=[b for b in builds if b['kind']=='task' and b['task']==name and b['exit_code']==0 and b['finished']<identity['captured']]
            assert latest and latest[-1]['image_id']==identity['image_id'] and latest[-1]['dockerfile_sha256']==identity['dockerfile_sha256']
            source_bound.append(identity)
        if flags['complete_parseable_pair']:assert len(source_bound)==2 and unchanged in outer
        for identity in source_bound:
            assert identity['bootstrap_dependency_image_id']==report['bootstrap_replay']['image_id']
            assert identity['dependency_ancestry_verified'] and identity['dependency_ancestry'][-1]==identity['bootstrap_dependency_image_id']
            assert identity['effective_test_path_exports']==config['effective_test_path_exports']
            assert identity['test_commands_sha256']==config['test_commands_sha256']
        outcomes.append(dict(task=name,state=state['state'],original_task_identity=task['original_task_identity'],
            prepared_task_identity=task['prepared_task_identity'],rows=rows,**flags,
            image_identity_captures=len(source_bound),source_and_images_verified=bool(len(source_bound)==2),
            original_grading_assets_unchanged=8 if recipes_verified else None))
    bootstrap=report.get('bootstrap_replay')
    if bootstrap:
        assert json.loads(outer['bootstrap/bootstrap-replay.json']['data'])==bootstrap
        assert bootstrap['descriptor_sha256']==sha(ROOT/'bootstrap-dependency.json')
        if bootstrap['stage']=='dependency_verified':
            descriptor=json.loads((ROOT/'bootstrap-dependency.json').read_text())
            actions=json.loads((ROOT/family['payload_directory']/'recorded-actions.json').read_text())['actions']
            assert bootstrap['base_image_id']==descriptor['expected_base_image_id']
            assert bootstrap['source_commit']==descriptor['bootstrap_ref'] and bootstrap['actions_sha256']==descriptor['actions_sha256']
            assert bootstrap['smoke_passed'] and bootstrap['verify_passed']
            assert bootstrap['source_sandbox_removed_before_fresh_check'] and bootstrap['bootstrap_containers_removed']
            assert bootstrap['context_removed'] and bootstrap['docker_config_removed']
            assert bootstrap['replay']['status']=='matched_recorded_exits' and len(bootstrap['replay']['steps'])==len(actions)
        if report.get('controls_started'):assert bootstrap['stage']=='dependency_verified'
    cleanup=report.get('cleanup')
    if cleanup and cleanup.get('verified_no_creation'):
        assert not report.get('resource_creation_started') and input_verified and not report.get('controls_started')
    if report.get('controls_started') or report.get('bootstrap_build_started'):assert absence
    result=dict(run_id=family['run_id'],repo=config['repo'],job_state=account['state'],stage=report.get('stage','infrastructure_interrupted'),
        error_type=report.get('error_type'),error_phase=report.get('error_phase'),
        source_variant=config['source_variant'],archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        archive_members=[dict(path=n,bytes=r['bytes'],sha256=r['sha256']) for n,r in outer.items()],
        task_package_verified=recipes_verified,input_package_verified=input_verified,bootstrap_build_exit=report.get('bootstrap_build_exit'),
        actual_builds=builds,image_identities=identities,tasks=outcomes,bootstrap_replay=bootstrap,
        cleanup=cleanup,worker_id=report['worker_id'],original_images_absent=absence,
        allocated_cpu_hours=account['allocated_cpu_hours'],model_calls=0,task_repairs=0,
        public_base_repo_digests=(report.get('public_base_inspect') or {}).get('RepoDigests'),
        control_invocations_started=sum(r['state']!='unstarted' for t in outcomes for r in t['rows']),
        tasks_with_control_invocations=sum(any(r['state']!='unstarted' for r in t['rows']) for t in outcomes),
        complete_pairs=sum(t['complete_parseable_pair'] for t in outcomes),
        positive_tasks=sum(t['positive_control_pair'] for t in outcomes),clean_tasks=sum(t['clean_oracle_command'] for t in outcomes))
    target=directory/'readback.json'
    if target.exists():assert json.loads(target.read_text())==result
    else:write(target,result)
    return result
