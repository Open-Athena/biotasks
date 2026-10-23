"""Download original terminal control archive; verify and summarize without regrading."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import zstandard

ROOT=Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    account=json.loads((ROOT/'controls-accounting.json').read_text())
    assert account['state']=='succeeded' and account['attempts']==1
    a=account['output_archive'];assert a['state']=='uploaded' and a['size_bytes']<1024**2
    dest=ROOT/'inputs-private/controls-001';dest.mkdir(exist_ok=True)
    archive=dest/'outputs.tar.zst'
    if not archive.exists():subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud','storage','cp','--quiet',a['uri'],str(archive)],capture_output=True,check=True,timeout=90)
    assert archive.stat().st_size==a['size_bytes'] and sha(archive)==a['sha256']
    total=0;members=[]
    with archive.open('rb') as raw,zstandard.ZstdDecompressor().stream_reader(raw) as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
        for member in tar:
            if member.isdir():continue
            path=PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            total+=member.size;assert member.size<5*1024**2 and total<10*1024**2
            target=dest/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(member).read()
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data)
            members.append({'path':member.name,'bytes':len(data),'sha256':sha(target)})
    report=json.loads((dest/'control-result.json').read_text())
    assert report['cleanup']['verified_empty'] and report['archive_copied'] and report['controls_exit']==0
    for name,digest in report['output_sha256'].items():assert sha(dest/name)==digest
    unchanged=json.loads((dest/'controls/task-files-unchanged.json').read_text())
    assert unchanged['verified'] and unchanged['before']==unchanged['after']
    plan=json.loads((ROOT/'control-plan.json').read_text())
    original=next(r for r in plan['repositories'] if r['repo']=='matchms/matchms')
    assert unchanged['after']=={f['path']:f['sha256'] for t in original['tasks'] for f in t['original_files']}
    controls=json.loads((dest/'controls/controls.json').read_text())
    assert len(controls)==8
    rows=[]
    for control in controls:
        results=control['trial_results'];assert len(results)==1
        trial=results[0]['result']
        details=[json.loads(v) for k,v in control.get('reward_files',{}).items() if k.endswith('reward-details.json')]
        assert len(details)==1
        d=details[0]
        rows.append({'task':control['task'],'agent':control['agent'],'state':control['state'],'wrapper_exit':control['exit_code'],
                     'exception':trial['exception_info'],'reward':trial['verifier_result']['rewards']['reward'],
                     'parse_status':d['parse_status'],'resolved':d['resolved'],'command_resolved':d['command_resolved'],
                     'test_exit_code':d['exit_code'],'f2p_passed':d['f2p_passed'],'f2p_total':d['f2p_total'],
                     'p2p_passed':d['p2p_passed'],'p2p_total':d['p2p_total'],
                     'wall_seconds':control['finished']-control['started']})
    pairs=[]
    for task in original['tasks']:
        sides={r['agent']:r for r in rows if r['task']==task['task']};assert set(sides)=={'nop','oracle'}
        nop,oracle=sides['nop'],sides['oracle']
        positive=all(r['state']=='completed' and r['exception'] is None and r['parse_status']=='ok' for r in sides.values()) and nop['reward']==0 and oracle['reward']==1 and oracle['resolved']
        pairs.append({'task':task['task'],'positive_control_pair':bool(positive),'clean_oracle_command':oracle['command_resolved'] is True,'all_regression_tests_pass_both':all(r['p2p_passed']==r['p2p_total'] for r in sides.values())})
    output={'scope':'Original saved tasks on reconstructed environment; read original verifier results, no regrading or task repairs','rows':rows,'pairs':pairs,'positive_pairs':sum(p['positive_control_pair'] for p in pairs),'clean_oracle_commands':sum(p['clean_oracle_command'] for p in pairs),'task_files_unchanged':True,'verified_task_files':len(unchanged['after']),'archive_sha256':a['sha256'],'archive_members':members,'owned_control_resources_removed':True,'retained_reconstruction_image':report['retained_reconstruction_image'],'model_calls':0,'allocated_cpu_hours_reconstruction_and_controls':account['allocated_cpu_hours']+json.loads((ROOT/'reconstruction-accounting.json').read_text())['allocated_cpu_hours'],'limits':['Environment reconstructed from saved commands; deleted original image bytes not reproduced','Original mutable base/dependency versions can drift','Does not change verdicts of earlier attempts or count newly generated tasks','Protected Matchms raw artifacts retained privately; remote archive expires after seven days']}
    (ROOT/'matchms-control-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'positive_pairs':output['positive_pairs'],'clean_oracle_commands':output['clean_oracle_commands'],'pairs':pairs,'allocated_cpu_hours':output['allocated_cpu_hours_reconstruction_and_controls']}))

if __name__=='__main__':main()
