"""Verify archived build-stage and conditional control evidence; never repair/regrade."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import subprocess
import tarfile
import zstandard

ROOT=Path(__file__).resolve().parent
RUN='biotasks37-ohif-5996-inline-001'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def safe(name):
    path=PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return path


def read_control_rows(controls):
    rows = []
    for control in controls:
        assert control['task'] == 'OHIF__Viewers-5996'
        assert control['agent'] in ('nop', 'oracle') and control['verifier_timeout_seconds'] == 300
        trials = control.get('trial_results', [])
        assert len(trials) <= 1
        trial = trials[0]['result'] if trials else {}
        details = [json.loads(value) for name, value in control.get('reward_files', {}).items() if name.endswith('reward-details.json')]
        assert len(details) <= 1
        detail = details[0] if details else {}
        rows.append(dict(task=control['task'], agent=control['agent'], verifier_timeout_seconds=300,
            state=control['state'], wrapper_exit=control.get('exit_code'), trial_record_present=bool(trial),
            reward_details_present=bool(details), exception_present=bool(trial.get('exception_info')),
            reward=((trial.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
            parse_status=detail.get('parse_status'), resolved=detail.get('resolved'),
            command_resolved=detail.get('command_resolved'), test_exit_code=detail.get('exit_code'),
            f2p_passed=detail.get('f2p_passed'), f2p_total=detail.get('f2p_total'),
            p2p_passed=detail.get('p2p_passed'), p2p_total=detail.get('p2p_total')))
    assert len({r['agent'] for r in rows}) == len(rows) <= 2
    return rows

def classify_pair(rows, seconds=300):
    sides={r['agent']:r for r in rows if r['verifier_timeout_seconds']==seconds}
    complete=set(sides)=={'nop','oracle'} and all(r['state']=='completed' and r['wrapper_exit']==0 and r['trial_record_present'] and r['reward_details_present'] and not r['exception_present'] and r['parse_status']=='ok' for r in sides.values())
    positive=complete and sides['nop']['reward']==0 and sides['oracle']['reward']==1 and sides['oracle']['resolved'] is True
    regressions=complete and all(r['p2p_total'] is not None and r['p2p_passed']==r['p2p_total'] for r in sides.values())
    return {'verifier_timeout_seconds':seconds,'complete_parseable_pair':complete,'positive_control_pair':positive,
              'clean_oracle_command':bool(complete and sides['oracle']['command_resolved'] is True),
              'all_regression_tests_pass_both':regressions}


def main():
    account=json.loads((ROOT/'cold-accounting.json').read_text())
    assert account['job_id']=='/exedev/'+RUN and account['attempts']==1
    assert account['state'] in ('succeeded','failed')
    spec=account['output_archive'];assert spec['state']=='uploaded' and spec['size_bytes']<8*1024**2
    dest=ROOT/'inputs-private/cold-output';dest.mkdir(mode=0o700,parents=True,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',spec['uri'],str(archive)],check=True,capture_output=True,timeout=90)
    assert archive.stat().st_size==spec['size_bytes'] and sha(archive)==spec['sha256']
    seen=set();members=[];total=0
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            name=safe(member.name)
            if member.isdir():continue
            assert member.isfile() and member.name not in seen and member.size<8*1024**2
            seen.add(member.name);total+=member.size;assert total<16*1024**2
            data=tar.extractfile(member).read();assert len(data)==member.size
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert not target.is_symlink() and target.read_bytes()==data
            else:target.write_bytes(data);target.chmod(0o600)
            members.append(dict(path=member.name,bytes=member.size,sha256=sha(target)))
    report=json.loads((dest/'control-result.json').read_text())
    assert report['run_id']==RUN and report['model_calls']==0
    assert report['payload_sha256']==json.loads((ROOT/'cold-payload-manifest.json').read_text())['sha256']
    for name,digest in report.get('output_sha256',{}).items():assert sha(dest/safe(name))==digest
    inputs=json.loads((ROOT/'cold-worker-inputs.json').read_text())
    expected={f['path']:f for f in inputs['files']}
    packed={}
    with tarfile.open(dest/'control-artifacts.tar.gz') as tar:
        for member in tar:
            safe(member.name)
            if member.isdir():continue
            assert member.isfile() and member.name not in packed and member.size<1024**2
            packed[member.name]=(tar.extractfile(member).read(),member.mode)
    assert {n for n in packed if n.startswith('outputs/')}==set(expected)
    for name,spec in expected.items():
        data,mode=packed[name]
        assert len(data)==spec['bytes'] and mode==int(spec['mode'],8) and hashlib.sha256(data).hexdigest()==spec['sha256']
    from harbor_docker_cold import tagged_recipe
    dockerfile_name=next(n for n in expected if n.endswith('/Dockerfile'))
    original=packed[dockerfile_name][0];digest=hashlib.sha256(original).hexdigest()
    effective=tagged_recipe(original,RUN)
    assert packed['infra/'+digest+'.Dockerfile'][0]==effective
    build_path=dest/'bounded-builds.jsonl'
    builds=[json.loads(line) for line in build_path.read_text().splitlines()] if build_path.exists() else []
    assert all(b['dockerfile_sha256']==digest for b in builds)
    assert all(b.get('effective_dockerfile_sha256',hashlib.sha256(effective).hexdigest())==hashlib.sha256(effective).hexdigest() for b in builds)
    log=(dest/'first-build.log').read_text()
    missing_tool=bool(re.search(r'(?:/bin/sh:\s*\d+:\s*)?pnpm:\s*(?:command )?not found',log))
    inner_exit=re.findall(r'returned a non-zero code:\s*(\d+)',log)
    controls_path=dest/'controls/controls.json'
    controls=json.loads(controls_path.read_text()) if controls_path.exists() else []
    rows=read_control_rows(controls);pair=classify_pair(rows) if rows else None
    negative=report.get('native_build_exit') is not None and report['native_build_exit']!=0
    if negative:
        assert len(builds)==1 and builds[0]['exit_code']==report['native_build_exit']
        assert report['native_build_started']<=builds[0]['started']<builds[0]['finished']<=report['native_build_finished']
        assert report['controls_skipped'] and not controls and 'controls_started' not in report
        assert 'setup_exit' not in report and not (dest/'setup.log').exists()
    raw_logs=[]
    for control in controls:
        prefix='jobs/ohif-5996-controls/'
        for trial in control.get('trial_results',[]):assert json.loads(packed[prefix+trial['path']][0])==trial['result']
        for name,value in control.get('reward_files',{}).items():assert packed[prefix+name][0].decode()==value
        for name,(data,_) in packed.items():
            if '-300s-'+control['agent']+'/' in name and name.endswith('/verifier/test-stdout.txt'):
                raw_logs.append(dict(agent=control['agent'],path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    submission=json.loads((ROOT/'run-private'/RUN/'submission.json').read_text())
    excluded=json.loads((ROOT/'inputs-private/original-workers.json').read_text())
    worker=report.get('worker_id')
    worker_verified=bool(report.get('different_worker_verified') and worker==submission['worker_id'] and
        worker not in excluded['excluded_worker_ids'] and worker.rsplit('-worker-',1)[0] not in excluded['excluded_tpu_names'])
    absence=report.get('original_image_absence')=={ref:True for ref in inputs['original_worker_state_refs']}
    base=report.get('public_base_inspect') or {}
    result=dict(run_id=RUN,job_state=account['state'],task=inputs['task'],
        source_variant=inputs['source_variant'],original_task_identity=inputs['original_task_identity'],
        prepared_task_identity=inputs['prepared_task_identity'],
        stage='native_image_build_failed' if negative else report.get('scientific_stage','incomplete'),
        native_build_exit=report.get('native_build_exit'),native_build_inner_exit=int(inner_exit[-1]) if inner_exit else None,
        missing_pnpm_observed=missing_tool,controls_skipped=report.get('controls_skipped'),
        actual_builds=builds,rows=rows,pair=pair,raw_control_logs_verified=raw_logs,
        different_worker_verified=worker_verified,original_images_absent=absence,
        selected_task_files_verified=10,original_grading_assets_unchanged=8,effective_recipe_label_only_verified=True,
        public_base_id=base.get('Id'),public_base_repo_digests=base.get('RepoDigests'),
        image_identities=report.get('image_identities',[]),
        owned_resources_removed=report.get('cleanup',{}).get('verified_empty',False),
        archive_sha256=sha(archive),archive_members=members,
        allocated_cpu_hours=account['allocated_cpu_hours'],model_calls=0,task_repairs=0,
        limits=['One existing export attempt; no new unique cohort task',
            'Diagnostic job success does not establish task/control success',
            'No test result or model score exists when build prevents controls',
            'Native registry distribution and changes to recipe generation remain untested'])
    (ROOT/'runtime-readback.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('archive_members','actual_builds','image_identities','limits')}))


if __name__=='__main__':main()

