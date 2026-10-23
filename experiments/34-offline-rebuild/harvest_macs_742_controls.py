"""Read the candidate MACS PR742 Harbor controls without regrading."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zstandard

ROOT=Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def classify_pair(rows, seconds=300):
    sides={r['agent']:r for r in rows if r['verifier_timeout_seconds']==seconds}
    complete=set(sides)=={'nop','oracle'} and all(r['state']=='completed' and r['wrapper_exit']==0 and r['trial_record_present'] and r['reward_details_present'] and not r['exception_present'] and r['parse_status']=='ok' for r in sides.values())
    positive=complete and sides['nop']['reward']==0 and sides['oracle']['reward']==1 and sides['oracle']['resolved'] is True
    regressions=complete and all(r['p2p_total'] is not None and r['p2p_passed']==r['p2p_total'] for r in sides.values())
    return {'verifier_timeout_seconds':seconds,'complete_parseable_pair':complete,'positive_control_pair':positive,
              'clean_oracle_command':bool(complete and sides['oracle']['command_resolved'] is True),
              'all_regression_tests_pass_both':regressions}


def main():
    account=json.loads((ROOT/'macs-742-controls-accounting.json').read_text())
    assert account['state'] in ('succeeded','failed') and account['attempts']==1
    a=account['output_archive'];assert a['state']=='uploaded' and a['size_bytes']<16*1024**2
    dest=ROOT/'inputs-private/macs-742-controls-001';dest.mkdir(mode=0o700,exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',a['uri'],str(archive)],capture_output=True,check=True,timeout=90)
    assert archive.stat().st_size==a['size_bytes'] and sha(archive)==a['sha256']
    members=[];total=0;seen=set()
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for m in tar:
            path=PurePosixPath(m.name);assert not path.is_absolute() and '..' not in path.parts
            assert m.name not in seen;seen.add(m.name)
            if m.isdir():continue
            assert m.isfile() and m.size<16*1024**2
            total+=m.size;assert total<64*1024**2
            target=dest/m.name;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(m).read()
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data);target.chmod(0o600)
            members.append({'path':m.name,'bytes':len(data),'sha256':sha(target)})
    report=json.loads((dest/'control-result.json').read_text())
    assert report['run_id']=='biotasks34-macs-742-controls-001' and report['model_calls']==0
    for name,digest in report.get('output_sha256',{}).items():
        path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
        assert sha(dest/name)==digest
    (ROOT/'macs-742-controls-result-001.json').write_text(json.dumps(report,indent=2)+'\n')
    unchanged_path=dest/'controls/task-files-unchanged.json'
    unchanged=json.loads(unchanged_path.read_text()) if unchanged_path.exists() else None
    plan=json.loads((ROOT/'offline-control-plan.json').read_text())
    original=next(r for r in plan['repositories'] if r['repo']=='macs3-project/MACS')
    expected={f['path']:f['sha256'] for t in original['tasks'] for f in t['original_files']}
    assert len(expected)==12
    if unchanged:assert unchanged['verified'] and unchanged['before']==unchanged['after']==expected
    cp=dest/'controls/controls.json'
    controls=json.loads(cp.read_text()) if cp.exists() else []
    if controls:assert len(controls)==2
    rows=[]
    for control in controls:
        results=control.get('trial_results',[]);assert len(results)<=1
        trial=results[0]['result'] if results else {}
        details=[json.loads(v) for k,v in control.get('reward_files',{}).items() if k.endswith('reward-details.json')]
        assert len(details)<=1
        d=details[0] if details else {}
        verifier=trial.get('verifier_result') or {}
        exception=trial.get('exception_info')
        rows.append({'task':control['task'],'agent':control['agent'],'verifier_timeout_seconds':control['verifier_timeout_seconds'],
                     'state':control['state'],'wrapper_exit':control.get('exit_code'),'trial_record_present':bool(trial),'reward_details_present':bool(details),
                     'exception_type':exception.get('exception_type') if isinstance(exception,dict) else type(exception).__name__ if exception else None,
                     'exception_present':bool(exception),'reward':(verifier.get('rewards') or {}).get('reward'),
                     'parse_status':d.get('parse_status'),'resolved':d.get('resolved'),'command_resolved':d.get('command_resolved'),
                     'test_exit_code':d.get('exit_code'),'f2p_passed':d.get('f2p_passed'),'f2p_total':d.get('f2p_total'),
                     'p2p_passed':d.get('p2p_passed'),'p2p_total':d.get('p2p_total'),'reason':control.get('reason'),
                     'wall_seconds':control['finished']-control['started'] if 'finished' in control else None})
    receipts=[]
    declared=json.loads((ROOT/'macs-base-dependency-plan.json').read_text())
    for item in report.get('dependency_receipts',[]):
        path=PurePosixPath(item['file'])
        assert len(path.parts)==1 and path.name.startswith('dependency-receipt-')
        receipt_path=dest/path.name
        assert sha(receipt_path)==item['sha256']==report['output_sha256'][path.name]
        receipt=json.loads(receipt_path.read_text())
        for key in ('base_commit','target_distribution','pyproject_sha256','build_requirements','build_backend'):
            assert receipt['plan'][key]==declared[key]
        assert receipt['wheels'] and not any(w['name']=='macs3' for w in receipt['wheels'])
        receipts.append(dict(item, receipt=receipt))
    preparation_verified=bool(receipts) and not report.get('dependency_receipt_error')
    pairs=[classify_pair(rows)]
    image=json.loads((ROOT/'macs-742-image-result-001.json').read_text())
    image_matches=report.get('retained_reconstruction_image')==image['retained_image_tag'] and report.get('bootstrap_image_id')==image['retained_image_id']
    output={'scope':'Read offline dependency-cache PR742 controls; original verifier, patch, timeout and egress guard unchanged; no regrading or repair',
            'job_state':account['state'],'rows':rows,'pairs':pairs,'task_files_unchanged':bool(unchanged),'verified_task_files':len(expected) if unchanged else 0,
            'comparison_provenance_verified':bool(unchanged and preparation_verified and image_matches),
            'reconstruction_image_matches':image_matches,'dependency_preparation_verified':preparation_verified,'dependency_receipts':receipts,'dependency_receipt_error':report.get('dependency_receipt_error'),
            'archive_sha256':a['sha256'],'archive_members':members,'owned_control_resources_removed':report.get('cleanup',{}).get('verified_empty',False),
            'retained_reconstruction_image':report.get('retained_reconstruction_image'),'model_calls':0,'allocated_cpu_hours_controls':account['allocated_cpu_hours'],
            'limits':['Candidate export used archived inputs and the pinned upstream writer; it is not a fresh official generate CLI run','Reconstructed environment is not the deleted original image; mutable dependencies can drift','Smoke and fresh-image checks passed before controls','Unstarted/timed-out/missing-reward trials are not positive controls','One nop/oracle pair is one candidate task, not a benchmark score','Dependency receipt records preparation; passing controls remain a separate gate','Owned reconstructed image requires separate cleanup after readback']}
    (ROOT/'macs-742-control-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('archive_members','limits')}))

if __name__=='__main__':main()
