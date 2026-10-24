"""Controls-only Harbor invocation; immutable selected task files and explicit deadlines.

Run only inside a checkpointed, resource-bounded remote supervisor. The supervisor
must remove its owned containers on interruption/timeout; this runner stops after
any wrapper timeout and never starts another trial in that condition.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib

ROOT=Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inspect_tasks(repo, root):
    hashes={}
    for task in repo['tasks']:
        expected={f['path']:f for f in task['original_files']}
        directory=root/'outputs'/repo['slug']/task['task']
        actual={str(p.relative_to(root)) for p in directory.rglob('*') if p.is_file()}
        assert actual==set(expected),'Task file inventory differs'
        for name,spec in expected.items():
            path=root/name
            assert not path.is_symlink() and path.stat().st_size==spec['bytes']
            assert path.stat().st_mode & 0o777 == int(spec['mode'],8)
            hashes[name]=digest(path);assert hashes[name]==spec['sha256']
        config=tomllib.loads((directory/'task.toml').read_text())
        assert config['verifier']['timeout_sec']==300
    return hashes


def commands(repo, root, harbor, jobs):
    rows=[]
    for task in repo['tasks']:
        for seconds in task['proposed_arms_seconds']:
            assert seconds in (300,1200)
            for agent in ['nop','oracle']:
                name=f"{task['task']}-{seconds}s-{agent}"
                cmd=[str(harbor),'run','-p',str(root/'outputs'/repo['slug']/task['task']),'-a',agent,
                     '--env','docker','-n','1','-k','1','-r','0','--override-cpus','1',
                     '--override-memory-mb','6144','--verifier-timeout-multiplier',str(seconds//300),
                     '-o',str(jobs),'--job-name',name]
                rows.append({'task':task['task'],'agent':agent,'verifier_timeout_seconds':seconds,
                             'name':name,'command':cmd,'wrapper_allowance_seconds':2*seconds+300,
                             'state':'unstarted'})
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',required=True)
    p.add_argument('--tasks-root',type=Path,required=True)
    p.add_argument('--harbor',type=Path,default=Path('/work/harbor066/bin/harbor'))
    p.add_argument('--jobs',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--deadline',type=float)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    plan=json.loads((ROOT/'control-plan.json').read_text())
    repo=next(r for r in plan['repositories'] if r['repo']==args.repo)
    before=inspect_tasks(repo,args.tasks_root)
    rows=commands(repo,args.tasks_root,args.harbor,args.jobs)
    args.evidence.mkdir(parents=True,exist_ok=True)
    target=args.evidence/'controls.json'
    assert not target.exists(),'Never overwrite prior execution evidence'
    def save():target.write_text(json.dumps(rows,indent=2)+'\n')
    save()
    if not args.execute:
        print(json.dumps({'mode':'dry_run','commands':len(rows),'files_verified':len(before),'total_wrapper_allowance_seconds':sum(r['wrapper_allowance_seconds'] for r in rows)}));return
    assert args.deadline is not None
    # The caller must provide this explicit declaration from its supervisor.
    assert os.environ.get('BIOTASKS29_BOUNDED_SUPERVISOR')=='1'
    assert not args.jobs.exists(),'Use an unused jobs directory for each invocation'
    args.jobs.mkdir(parents=True)
    version=subprocess.check_output([str(args.harbor),'--version'],text=True,timeout=15).strip()
    assert '0.6.6' in version
    (args.evidence/'harbor-version.txt').write_text(version+'\n')
    env=os.environ.copy()
    for key in ['GH_TOKEN','GITHUB_TOKEN','OPENROUTER_API_KEY']:env.pop(key,None)
    try:
        for row in rows:
            allowance=row['wrapper_allowance_seconds']
            if time.time()+allowance+300>args.deadline:
                row['reason']='insufficient_full_trial_and_cleanup_reserve';save();break
            row.update(state='running',started=time.time());save()
            try:
                with (args.evidence/(row['name']+'.log')).open('w') as log:
                    result=subprocess.run(row['command'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=allowance,check=False)
                row.update(state='completed',exit_code=result.returncode,finished=time.time())
            except subprocess.TimeoutExpired:
                row.update(state='wrapper_timeout',finished=time.time(),reason='supervisor_must_remove_owned_containers_before_any_later_trial');save();return 124
            row['trial_results']=[{'path':str(path.relative_to(args.jobs)),'result':json.loads(path.read_text())} for path in sorted((args.jobs/row['name']).glob('*/result.json'))]
            row['reward_files']={str(path.relative_to(args.jobs)):path.read_text() for path in sorted((args.jobs/row['name']).rglob('reward*')) if path.is_file() and path.stat().st_size<100000}
            save()
    finally:
        after=inspect_tasks(repo,args.tasks_root)
        (args.evidence/'task-files-unchanged.json').write_text(json.dumps({'verified':before==after,'before':before,'after':after},indent=2)+'\n')
        assert before==after
        save()
    return 0

if __name__=='__main__':raise SystemExit(main())
