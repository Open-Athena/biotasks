"""Reconcile existing Scanpy evidence and classify unmodified transfer limits."""
import ast
import json
from pathlib import Path
import re
import tomllib

from common import UPSTREAM,content_sha,json_sha,sha,task_identity,write
from evidence import archive_records

ROOT=Path(__file__).resolve().parent


def verified_output(path,report_name):
    rows=archive_records(path,'tar.zst');report=json.loads(rows[report_name]['data'])
    for name,digest in report.get('output_sha256',{}).items():assert rows[name]['sha256']==digest
    return rows,report


def main():
    plan=json.loads((ROOT/'source-plan.json').read_text());acq=json.loads((ROOT/'acquisition.json').read_text())
    assert acq['anonymous_download_verified'] and acq['remote_jobs']==acq['model_calls']==0
    for row in acq['files']:assert sha(ROOT/row['path'])==row['sha256']
    tree=ROOT.parents[2];source=tree/'31/experiments/31-historical-builds'
    pins=json.loads((source/'package-acquisition.json').read_text());package=source/'inputs-private/upstream-package'
    assert pins['revision']==UPSTREAM and len(pins['files'])==353
    for row in pins['files']:assert sha(package/row['path'])==row['sha256']
    native=package/'src/repo2rlenv';runner=(native/'bootstrap/runner.py').read_text()
    ledger=tree/'33/experiments/33-unattended-validation/task-execution-ledger.json'
    assert sha(ledger)=='19295d776ba31861e605da2da13c9e364ade163ed2ac778d7a39b81b8af0d302'
    task=next(t for t in json.loads(ledger.read_text())['tasks'] if t['task']==plan['task'])
    acquired=ROOT/'inputs-private/acquired';phase=archive_records(acquired/'original-phase.tar.gz','tar.gz')
    original_manifest=json.loads((acquired/'original-manifest.json').read_text())
    expected=next(f for f in original_manifest['files'] if f['path']=='evidence/phase-artifacts.tar.gz')
    assert sha(acquired/'original-phase.tar.gz')==task['original_phase_sha256']==expected['sha256']
    transcripts=[(n,r) for n,r in phase.items() if n.startswith('bootstrap/') and n.endswith('/transcript.jsonl')];assert len(transcripts)==1
    name,transcript=transcripts[0];boot_name=name.rsplit('/',1)[0]+'/bootstrap.json';boot_raw=phase[boot_name]['data'];boot=json.loads(boot_raw)
    assert boot['repo']==plan['repo'] and boot['ref']=='903925920218f829f3cad4f9f4730c086267ee53'
    turns=[json.loads(line) for line in transcript['data'].splitlines()];actions=[]
    assert [t['step'] for t in turns]==sorted(set(t['step'] for t in turns))
    assert set(t['action'] for t in turns)=={'BASH'}
    for turn in turns:
        code=int(re.match(r'^exit=(\d+)\n',turn['observation'])[1]);assert code!=124
        actions.append(dict(step=turn['step'],command=turn['input'],command_sha256=content_sha(turn['input'].encode()),
            expected_exit_code=code,original_observation_sha256=content_sha(turn['observation'].encode()),timeout_seconds=300))
    base=re.search(r'^FROM (.+)$',boot['dockerfile_reconstruction'],re.M)[1]
    regenerated='\n'.join(['# Auto-generated from r2e-bootstrap agent transcript.','# Build from the cloned repo root: `docker build -t my-image .`',f'FROM {base}','WORKDIR /workspace','COPY . /workspace','']+['RUN '+a['command'].replace('\n',' \\\n    ') for a in actions]+[''])
    assert regenerated==boot['dockerfile_reconstruction']
    payload=dict(repo=boot['repo'],ref=boot['ref'],base_image=base,actions=actions,test_cmds=boot['test_cmds'],rebuild_cmds=boot['rebuild_cmds'],original_smoke_passed=boot['smoke_passed'],original_verify_passed=boot['verify_passed'])
    raw=(json.dumps(payload,indent=2)+'\n').encode();assert content_sha(raw)==plan['retained_replay_input']['sha256']
    assert len(actions)==16 and [(a['step'],a['expected_exit_code']) for a in actions if a['expected_exit_code']]==[(7,1)]
    original_dir='outputs/scverse__scanpy/'+plan['task']+'/'
    files=[dict(path=r['path'],bytes=phase[original_dir+r['path']]['bytes'],mode=format(phase[original_dir+r['path']]['mode'],'o'),sha256=phase[original_dir+r['path']]['sha256']) for r in task['original_task_files']]
    for row,old in zip(files,task['original_task_files'],strict=True):assert row['sha256']==old['sha256'] and int(row['mode'],8)==old['mode']
    assert task_identity(plan['repo'],plan['task'],files)==plan['original_task_identity']
    toml=tomllib.loads(phase[original_dir+'task.toml']['data'].decode());assert toml['verifier']['timeout_sec']==300
    targets={k:len(json.loads(phase[original_dir+'tests/'+k+'.json']['data'])) for k in ['f2p','p2p']}
    replay,report=verified_output(acquired/'recorded.tar.zst','scanpy-recorded-result.json')
    assert report['source_commit']==boot['ref'] and report['payload_sha256']==content_sha(raw) and report['commands_edited'] is False and report['model_calls']==0
    for old,key in [('docker_original.py','bootstrap/docker.py'),('runner_original.py','bootstrap/runner.py'),('auth_original.py','auth.py')]:assert report['source_sha256'][old]==sha(native/key)
    assert report['replay']['status']=='matched_recorded_exits' and not report['replay']['unstarted_steps']
    assert json.loads(replay['actions/replay.json']['data'])==report['replay']
    for action,step in zip(actions,report['replay']['steps'],strict=True):
        for key in ['step','command_sha256','expected_exit_code','timeout_seconds']:assert action[key]==step[key]
        assert step['exit_code']==action['expected_exit_code']
        for stream in ['stdout','stderr']:
            row=replay['actions/step-'+format(step['step'],'03d')+'-'+stream+'.txt'];assert row['sha256']==step[stream+'_sha256'] and row['bytes']==step[stream+'_bytes']
    calls=[json.loads(line) for line in replay['docker-calls.jsonl']['data'].splitlines()]
    assert not report['smoke_passed'] and not report['verify_passed']
    assert calls[-1]['sequence']==27 and calls[-1]['docker_operation']=='run' and calls[-1]['exit_code']==2
    assert next(c for c in calls if c['sequence']==23)['exit_code']==2
    fresh_log=replay['call-027-stdout.txt']['data'].decode()
    for marker in ['Pandas4Warning',"'flaky' not found",'dependency_groups','3 errors']:assert marker in fresh_log
    controls,control_report=verified_output(acquired/'controls.tar.zst','control-result.json')
    assert control_report['bootstrap_image_id']==report['image_id']
    packed=archive_records(controls['control-artifacts.tar.gz']['data'],'tar.gz')
    for row in files:assert packed[original_dir+row['path']]['sha256']==row['sha256'] and packed[original_dir+row['path']]['mode']==int(row['mode'],8)
    controls_json=json.loads(controls['controls/controls.json']['data']);assert len(controls_json)==4
    outcomes=[]
    for control in controls_json:
        assert control['task']==plan['task'] and control['state']=='completed' and control['exit_code']==0
        assert len(control['trial_results'])==1
        trial_row=control['trial_results'][0];trial=trial_row['result']
        assert json.loads(packed['jobs/scanpy-controls/'+trial_row['path']]['data'])==trial
        error=trial['exception_info'];assert error['exception_type']=='VerifierTimeoutError'
        assert not trial.get('verifier_result') and not control['reward_files']
        timeout=control['verifier_timeout_seconds'];assert timeout in [300,1200]
        logs=[(n,row) for n,row in packed.items() if n.startswith('jobs/scanpy-controls/'+control['name']+'/') and n.endswith('/verifier/test_output.log')];assert len(logs)==1
        log_name,log=logs[0];text=log['data'].decode();percentages=[int(s) for s in re.findall(r'\[\s*(\d+)%\]',text)]
        last_tests=[s.replace('\x00','') for s in text.splitlines() if 'tests/' in s][-4:]
        outcomes.append(dict(agent=control['agent'],timeout_seconds=timeout,trial_path=trial_row['path'],trial_sha256=packed['jobs/scanpy-controls/'+trial_row['path']]['sha256'],
            exception_type=error['exception_type'],reward=None,scientific_pair_validity='unmeasured_timeout',
            raw_log_path=log_name,raw_log_sha256=log['sha256'],raw_log_bytes=log['bytes'],raw_log_nul_bytes=log['data'].count(b'\0'),
            maximum_printed_progress_percent=max(percentages),pytest_collected_items=[int(n) for n in re.findall(r'collected (\d+) items?',text)],last_test_lines=last_tests,failed_test_lines=[s.replace('\x00','') for s in text.splitlines() if ' FAILED' in s][-8:]))
    assert {(r['agent'],r['timeout_seconds']) for r in outcomes}=={(a,t) for a in ['nop','oracle'] for t in [300,1200]}
    cleanup=archive_records(acquired/'cleanup.tar.zst','tar.zst');cleanup_report=json.loads(cleanup['cleanup-result.json']['data']);assert cleanup_report['verified_empty'] and not cleanup_report['remaining_containers'] and not cleanup_report['remaining_images']
    baseline,baseline_report=verified_output(acquired/'native-runtime.tar.zst','result.json')
    assert baseline_report['bootstrap_build_exit']==100 and not baseline_report.get('controls_started')
    base_inspect=baseline_report['public_base_inspect'];assert base_inspect['Id']==report['base_image_id']
    digests=base_inspect['RepoDigests'];assert len(digests)==1 and re.fullmatch(r'python@sha256:[0-9a-f]{64}',digests[0])
    log=baseline['bootstrap-build.log']['data'].decode();assert 'Unable to locate package cmake' in log and 'Unable to locate package python3.13' in log
    prepared=archive_records(acquired/'native-tasks.tar.gz','tar.gz');assert set(prepared)=={original_dir+r['path'] for r in files}
    prepared_files=[dict(row,path=row['path'],sha256=prepared[original_dir+row['path']]['sha256'],bytes=prepared[original_dir+row['path']]['bytes'],mode=format(prepared[original_dir+row['path']]['mode'],'o')) for row in files]
    assert task_identity(plan['repo'],plan['task'],prepared_files)==plan['native_inline_identity']
    unchanged=[r['path'] for r in files if prepared[original_dir+r['path']]['sha256']==r['sha256']];assert len(unchanged)==8
    script=phase[original_dir+'tests/test.sh']['data'].decode();assert script==prepared[original_dir+'tests/test.sh']['data'].decode()
    assert '( . /workspace/.venv/bin/activate && ' in script and not re.findall(r'^export PATH=',script,re.M)
    wrapper=tree/'39/experiments/39-recorded-bootstrap';init=(wrapper/'bootstrap_init.py').read_text();bridge=(wrapper/'docker_bridge.py').read_text()
    assert "if not namespace['smoke_ok']:" in init and "self.report['stage']='original_smoke_failed';return False" in init
    assert "assert len(exports)==2" in bridge
    assert '# Commit the container regardless' in runner and 'image is cached but flagged' in runner
    for name in ['pipelines/pr_runtime.py','pipelines/pr_runtime_validate.py']:
        refs=[n.attr for n in ast.walk(ast.parse((native/name).read_text())) if isinstance(n,ast.Attribute) and n.attr in ['smoke_passed','verify_passed']]
        assert not refs
    evidence=ROOT/'inputs-private/derived';evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'recorded-actions.json').write_bytes(raw);(evidence/'original-bootstrap.json').write_bytes(boot_raw)
    rows=dict(issue=40,kind='Source-bound retrospective evidence and unmodified-interface assessment; no new runtime',upstream_revision=UPSTREAM,
        original_task_identity=plan['original_task_identity'],native_inline_identity=plan['native_inline_identity'],original_grading_assets_unchanged=8,
        task_targets=targets,task_verifier_seconds=300,source_plan_sha256=sha(ROOT/'source-plan.json'),acquisition_sha256=sha(ROOT/'acquisition.json'),
        source_files_verified=len(pins['files']),native_package_acquisition_sha256=sha(source/'package-acquisition.json'),
        phase_sha256=sha(acquired/'original-phase.tar.gz'),transcript_member=transcripts[0][0],transcript_sha256=transcript['sha256'],
        original_bootstrap_sha256=phase[boot_name]['sha256'],actions_sha256=content_sha(raw),actions=16,recorded_nonzero_exits=[dict(step=7,exit_code=1)],
        original_smoke_passed=boot['smoke_passed'],original_verify_passed=boot['verify_passed'],historical_replay_actions_matched=True,
        historical_smoke_passed=report['smoke_passed'],historical_verify_passed=report['verify_passed'],historical_fresh_exit=2,
        fresh_collection_failures=['pandas future.infer_string deprecation promoted to error','unregistered flaky pytest marker','missing dependency_groups in ci/scripts/low-vers.py'],
        exact_public_base_id_matches_native_baseline=True,public_base_image_id=base_inspect['Id'],public_base_digest=digests[0],bootstrap_source_ref=boot['ref'],historical_replay_image_id=report['image_id'],
        historical_controls=outcomes,historical_control_task_files_unchanged=10,historical_owned_cleanup_verified=True,
        native_baseline_build_exit=100,native_baseline_controls_started=False,
        strict39_transfer='unsupported_as_is',hard_gate_difference='Upstream caches/returns failed smoke/verify flags; #39 rejects failed smoke before commit and failed fresh checks before task controls. This is outer acceptance policy, not an upstream rejection.',
        probe_interface_difference='Unchanged Scanpy verifier activates .venv; OHIF probe requires two PATH exports and would not measure the verifier environment as-is.',
        policy_source_sha256={n:sha(wrapper/n) for n in ['bootstrap_init.py','docker_bridge.py']},
        native_semantics_source_sha256={n:sha(native/n) for n in ['bootstrap/runner.py','pipelines/pr_runtime.py','pipelines/pr_runtime_validate.py']},
        new_remote_jobs=0,new_model_calls=0,new_allocated_cpu_hours=0,new_reservations=0,
        outcome='Retrospective negative transfer assessment, not a new failed runtime or fresh control score',
        decision='Do not repeat known unchanged replay/control failures or silently relax source/grading/timeout/acceptance contracts. Preserve this assessment and original public evidence.',
        limitations=['Timeout progress is incomplete output, not a pass rate or scored reward','Partial logs do not prove a hang or that extra time alone would produce valid controls','No new cold Scanpy rebuild or dependency identity equivalence claim','Recorded mutable installs can drift; no installation/test/config repair applied'])
    write(ROOT/'source-assessment.json',rows)
    print(json.dumps(dict(actions_verified=16,source_files_verified=353,original_grading_assets_unchanged=8,historical_timeout_trials=4,exact_public_base_matches=True,unmodified_transfer='unsupported_as_is',new_remote_jobs=0,new_model_calls=0)))


if __name__=='__main__':main()
