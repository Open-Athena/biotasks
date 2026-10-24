"""Read native trial/process/log bytes; never turn the fixture into a bio score."""
from datetime import datetime
import json
from pathlib import Path
import re

from common import sha,write
from evidence import archive_records

ROOT=Path(__file__).resolve().parent

import subprocess

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


def event_findings(events,raw):
    starts=[e for e in events if e['event']=='start'];ends=[e for e in events if e['event']=='end']
    assert len({e['token'] for e in starts})==len(starts)
    live=[]
    for event in starts:
        for prior in event['previous']:
            obs=prior['observed'];same=(obs.get('pid')==prior['expected_pid'] and obs.get('start_ticks')==prior['expected_start_ticks'])
            running=bool(same and obs.get('state') not in ['Z','X',None] and obs.get('writer_command'))
            if running:live.append(dict(observer_token=event['token'],prior_token=prior['expected_token'],observed_pid=obs['pid'],
                observed_state=obs['state'],same_start_ticks=True,observer_wall_ns=event['wall_ns'],
                same_log_inode=obs['fd1_inode']==event['self']['fd1_inode'],prior_offset=obs['fd1_offset'],new_offset=event['self']['fd1_offset'],
                prior_offset_exceeds_new_offset=obs['fd1_offset']>event['self']['fd1_offset']))
    samples=[e for e in events if e['event']=='sample'];holes=[e for e in samples if e['log_nul_bytes']>0]
    tokens={t.decode() for t in re.findall(rb'([0-9a-f]{32}):[0-9]{8}:x+\n',raw)}
    assert tokens<={e['token'] for e in starts}
    mechanism=bool(any(e['same_log_inode'] and e['new_offset']==0 and e['prior_offset_exceeds_new_offset'] for e in live) and holes and raw.count(b'\0')>0)
    return dict(writer_starts=len(starts),writer_ends=len(ends),live_prior_writers=live,
        native_container_sample_count=len(samples),in_container_hole_samples=len(holes),
        raw_log_nul_bytes=raw.count(b'\0'),raw_log_tokens=sorted(tokens),fixture_mechanism_observed=mechanism,
        historical_scanpy_cause_proven=False)


def readback(family,directory,gcloud='/home/exedev/.local/google-cloud-sdk/bin/gcloud'):
    directory=Path(directory);account=json.loads((directory/'accounting.json').read_text())
    assert account['job_id']=='/exedev/'+family['run_id'] and account['attempts']==1
    archive=download(account,directory,gcloud);outer=archive_records(archive,'tar.zst')
    report=json.loads((outer.get('result.json') or outer['work-state.json'])['data'])
    assert report['run_id']==family['run_id'] and report['payload_sha256']==family['payload_manifest']['sha256']
    submission=json.loads((directory/'submission.json').read_text());assert report['worker_id']==submission['worker_id'] and report['worker_constraint_verified']
    for name,digest in report.get('output_sha256',{}).items():assert outer[name]['sha256']==digest
    config=json.loads((ROOT/family['payload_directory']/'family.json').read_text())
    assert outer['input-package.tar.gz']['sha256']==config['task_bundle']['sha256']
    packed={};package_ok=False
    if 'control-artifacts.tar.gz' in outer:
        packed=archive_records(outer['control-artifacts.tar.gz']['data'],'tar.gz')
        expected={f['path']:f for f in config['task_bundle']['files']}
        assert {n for n in packed if n.startswith('outputs/')}==set(expected)
        for n,spec in expected.items():assert packed[n]['sha256']==spec['sha256'] and packed[n]['bytes']==spec['bytes'] and packed[n]['mode']==int(spec['mode'],8)
        package_ok=True
    builds=report.get('fixture_image_builds',[])
    for build in builds:
        if build['exit_code']==0:
            assert build['metadata_only'] and build['image_ref'].startswith(family['run_id']+'-')
            expected='FROM '+config['public_base_ref']+'\nLABEL biotasks.run='+family['run_id']+'\nLABEL biotasks.fixture='+build['case']+'\n'
            assert build['dockerfile_text']==expected
    probe=json.loads(outer['probe-results.json']['data']) if 'probe-results.json' in outer else {}
    parity=json.loads(outer['native-source-parity.json']['data']) if 'native-source-parity.json' in outer else {}
    if probe:assert probe['run_id']==family['run_id'] and probe['package_source_verified'] and parity['verified'] and parity['source_files_verified']==203
    cases=[]
    for row in probe.get('cases',[]):
        case=next(c for c in config['cases'] if c['name']==row['name']);prefix='jobs/'+family['run_id']+'-'+case['name']+'/'
        for f in row.get('files',[]):assert packed['jobs/'+f['path']]['sha256']==f['sha256'] and packed['jobs/'+f['path']]['bytes']==f['bytes']
        trials=row.get('trial_results',[]);assert len(trials)<=1
        for trial in trials:assert json.loads(packed['jobs/'+trial['path']]['data'])==trial['result'] and packed['jobs/'+trial['path']]['sha256']==trial['sha256']
        trial=trials[0]['result'] if trials else {}
        resources=row.get('resources')
        if resources:
            assert resources['owner_label']==family['run_id'] and resources['nano_cpus']==1000000000 and resources['memory_bytes']==6*1024**3 and resources['network']=='none'
            assert resources['image_id']==next(b['image_id'] for b in builds if b['case']==case['name'])
        event_rows=[(n,r) for n,r in packed.items() if n.startswith(prefix) and n.endswith('/verifier/process-events.jsonl')]
        log_rows=[(n,r) for n,r in packed.items() if n.startswith(prefix) and n.endswith('/verifier/writer.log')]
        assert len(event_rows)<=1 and len(log_rows)<=1
        events=[json.loads(line) for line in event_rows[0][1]['data'].splitlines()] if event_rows else []
        raw=log_rows[0][1]['data'] if log_rows else b''
        for event in events:
            if event['event']=='start':assert event['writer_seconds']==case['writer_seconds']
        finding=event_findings(events,raw)
        error=trial.get('exception_info');reward=((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward')
        expected={f['path'].removeprefix('outputs/'+config['id']+'/'+case['task']+'/'):f['sha256'] for f in config['task_bundle']['files'] if f['path'].startswith('outputs/'+config['id']+'/'+case['task']+'/')}
        if row.get('fixture_files_after'):assert row['fixture_files_before']==row['fixture_files_after']==expected
        cases.append(dict(name=case['name'],state=row['state'],wrapper_exit=row.get('wrapper_exit'),trial_present=bool(trial),exception=error,fixture_reward=reward,
            resources_verified=bool(resources),events_path=event_rows[0][0] if event_rows else None,writer_log_path=log_rows[0][0] if log_rows else None,
            writer_log_sha256=log_rows[0][1]['sha256'] if log_rows else None,events=events,**finding))
    finite=next((c for c in cases if c['name']=='finite'),None);timeout=next((c for c in cases if c['name']=='timeout'),None)
    finite_ok=bool(finite and finite['trial_present'] and not finite['exception'] and finite['fixture_reward']==0 and finite['writer_starts']==finite['writer_ends']==1 and finite['raw_log_nul_bytes']==0 and finite['resources_verified'])
    native_timeout=bool(timeout and (timeout['exception'] or {}).get('exception_type')=='VerifierTimeoutError' and timeout['fixture_reward'] is None)
    result=dict(run_id=family['run_id'],kind='native_harbor_infrastructure_fixture',worker_id=report['worker_id'],archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        archive_members=[dict(path=n,bytes=r['bytes'],sha256=r['sha256']) for n,r in outer.items()],
        input_package_verified=True,task_package_verified=package_ok,stage=report.get('stage','infrastructure_incomplete'),error_type=report.get('error_type'),error_phase=report.get('error_phase'),
        cases=cases,finite_control_passed=finite_ok,native_timeout_observed=native_timeout,
        fixture_mechanism_observed=bool(finite_ok and native_timeout and timeout['fixture_mechanism_observed'] and timeout['resources_verified']),
        historical_scanpy_cause_proven=False,native_source_parity=parity,owned_metadata_image_builds=builds,
        shared_public_base_preserved=report.get('shared_public_base_preserved',False),public_base_before=report.get('public_base_before'),
        build_context_removed=report.get('build_context_removed'),cleanup=report.get('cleanup'),allocated_cpu_hours=account['allocated_cpu_hours'],
        model_calls=0,original_tasks_changed=False,new_biological_tasks=0)
    path=directory/'readback.json'
    if path.exists():assert json.loads(path.read_text())==result
    else:write(path,result)
    return result
