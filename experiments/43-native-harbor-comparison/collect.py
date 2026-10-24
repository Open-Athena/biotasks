"""Read native trial/process/log bytes; never turn the fixture into a bio score."""
from datetime import datetime
import json
from pathlib import Path
import re

from common import sha,write
from evidence import archive_records
from readback_case import deadline_observations

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
        packed=archive_records(outer['control-artifacts.tar.gz']['data'],'tar.gz');expected={f['path']:f for f in config['task_bundle']['files']}
        assert {n for n in packed if n.startswith('outputs/')}==set(expected)
        for name,spec in expected.items():assert packed[name]['sha256']==spec['sha256'] and packed[name]['bytes']==spec['bytes'] and packed[name]['mode']==int(spec['mode'],8)
        package_ok=True
    builds=report.get('fixture_image_builds',[])
    for build in builds:
        if build['exit_code']==0:
            assert build['metadata_only'] and build['image_ref'].startswith(family['run_id']+'-')
            assert build['dockerfile_text']=='FROM '+config['public_base_ref']+'\nLABEL biotasks.run='+family['run_id']+'\nLABEL biotasks.fixture='+build['case']+'\n'
    probe=json.loads(outer['probe-results.json']['data']) if 'probe-results.json' in outer else {}
    parity=json.loads(outer['native-source-parity.json']['data']) if 'native-source-parity.json' in outer else {}
    packages=json.loads((ROOT/'package-acquisition.json').read_text())['packages']
    if probe:
        assert probe['run_id']==family['run_id'] and probe['package_source_verified'] and probe['timezone']=='UTC' and parity['verified']
        assert {p['version']:p['source_files_verified'] for p in parity['packages']}=={p['version']:len(p['source_files']) for p in packages}
    cases=[]
    for row in probe.get('cases',[]):
        case=next(c for c in config['cases'] if c['id']==row['id']);prefix='jobs/'+family['run_id']+'-'+case['id']+'/'
        if row['state'].startswith('skipped_'):
            cases.append(dict(id=case['id'],version=case['version'],name=case['name'],state=row['state'],measured=False));continue
        for item in row.get('files',[]):assert packed['jobs/'+item['path']]['sha256']==item['sha256'] and packed['jobs/'+item['path']]['bytes']==item['bytes']
        trials=row.get('trial_results',[]);assert len(trials)<=1
        for trial in trials:assert json.loads(packed['jobs/'+trial['path']]['data'])==trial['result'] and packed['jobs/'+trial['path']]['sha256']==trial['sha256']
        trial=trials[0]['result'] if trials else {};resources=row.get('resources')
        if resources:
            assert resources['owner_label']==family['run_id'] and resources['case_label']==case['id'] and resources['nano_cpus']==1000000000 and resources['memory_bytes']==6*1024**3 and resources['network']=='none'
            assert resources['image_id']==next(b['image_id'] for b in builds if b['case']==case['id'])
        event_rows=[(n,r) for n,r in packed.items() if n.startswith(prefix) and n.endswith('/verifier/process-events.jsonl')]
        log_rows=[(n,r) for n,r in packed.items() if n.startswith(prefix) and n.endswith('/verifier/writer.log')];assert len(event_rows)<=1 and len(log_rows)<=1
        events=[json.loads(line) for line in event_rows[0][1]['data'].splitlines()] if event_rows else [];raw=log_rows[0][1]['data'] if log_rows else b''
        for event in events:
            if event['event']=='start':assert event['writer_seconds']==case['writer_seconds']
        finding=event_findings(events,raw);docker_events=[]
        event_name=case['id']+'-docker-events.jsonl'
        if event_name in outer:
            assert outer[event_name]['sha256']==row['docker_events_sha256'] and outer[event_name]['bytes']==row['docker_events_bytes']
            docker_events=[json.loads(line) for line in outer[event_name]['data'].splitlines()]
            for event in docker_events:
                attrs=event.get('Actor',{}).get('Attributes',{});assert attrs['biotasks.run']==family['run_id'] and attrs['biotasks.case']==case['id']
        expected={f['path'].removeprefix(case['task_directory']+'/'):f['sha256'] for f in config['task_bundle']['files'] if f['path'].startswith(case['task_directory']+'/')}
        if row.get('fixture_files_after'):assert row['fixture_files_before']==row['fixture_files_after']==expected
        error=trial.get('exception_info');reward=((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward')
        cases.append(dict(id=case['id'],version=case['version'],name=case['name'],state=row['state'],measured=bool(trial),wrapper_exit=row.get('wrapper_exit'),exception=error,fixture_reward=reward,
            resources_verified=bool(resources),events_path=event_rows[0][0] if event_rows else None,writer_log_path=log_rows[0][0] if log_rows else None,
            writer_log_sha256=log_rows[0][1]['sha256'] if log_rows else None,events=events,observations=row.get('observations',[]),
            deadline_observations=deadline_observations(trial,row.get('observations',[]),docker_events),**finding))
    versions=[]
    for version in ['0.6.6','0.24.0']:
        finite=next((c for c in cases if c['version']==version and c['name']=='finite'),None);timeout=next((c for c in cases if c['version']==version and c['name']=='timeout'),None)
        finite_ok=bool(finite and finite.get('measured') and not finite['exception'] and finite['fixture_reward']==0 and finite['writer_starts']==finite['writer_ends']==1 and finite['raw_log_nul_bytes']==0 and finite['resources_verified'])
        native_timeout=bool(timeout and timeout.get('measured') and (timeout['exception'] or {}).get('exception_type')=='VerifierTimeoutError' and timeout['fixture_reward'] is None)
        versions.append(dict(version=version,finite_control_passed=finite_ok,native_timeout_observed=native_timeout,
            observed_timeout_writer_starts=timeout.get('writer_starts') if timeout else None,
            live_after_native_verifier_end_observed=(timeout.get('deadline_observations') or {}).get('live_writer_after_native_verifier_end_observed') if timeout else None))
    result=dict(run_id=family['run_id'],kind='native_harbor_version_infrastructure_comparison',worker_id=report['worker_id'],archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        input_package_verified=True,task_package_verified=package_ok,stage=report.get('stage','infrastructure_incomplete'),error_type=report.get('error_type'),error_phase=report.get('error_phase'),
        versions=versions,cases=cases,native_source_parity=parity,owned_metadata_image_builds=builds,probe_driver_exit=report.get('probe_driver_exit'),native_driver_completed=bool(probe.get('finished_ns')),
        shared_public_base_preserved=report.get('shared_public_base_preserved',False),cleanup=report.get('cleanup'),allocated_cpu_hours=account['allocated_cpu_hours'],
        model_calls=0,original_tasks_changed=False,new_biological_tasks=0,historical_scanpy_cause_proven=False)
    path=directory/'readback.json'
    if path.exists():assert json.loads(path.read_text())==result
    else:write(path,result)
    return result


