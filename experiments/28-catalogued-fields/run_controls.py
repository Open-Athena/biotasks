"""Official Harbor controls within a separately reserved window; no task edits."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def file_hashes(task):
    values = {}
    for path in task.rglob('*'):
        if path.is_file():
            with path.open('rb') as handle:
                values[str(path.relative_to(task))] = hashlib.file_digest(handle, 'sha256').hexdigest()
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--deadline', type=float, required=True)
    args = parser.parse_args()
    evidence = Path('/work/evidence')
    tasks = sorted(p.parent for p in args.tasks.rglob('task.toml'))
    (evidence / 'exported-tasks.json').write_text(json.dumps(
        [str(p.relative_to('/work')) for p in tasks], indent=2) + '\n')
    before = {str(task): file_hashes(task) for task in tasks}
    rows = [{'task': task.name, 'agent': agent, 'state': 'unstarted',
             'reason': 'not_reached_within_primary_control_allocation'}
            for task in tasks for agent in ['nop', 'oracle']]
    target = evidence / (args.prefix + '-controls.json')

    def save():
        target.write_text(json.dumps(rows, indent=2) + '\n')

    save()
    environment = os.environ.copy()
    for name in ['GH_TOKEN', 'GITHUB_TOKEN', 'OPENROUTER_API_KEY']:
        environment.pop(name, None)
    environment['PATH'] = '/work/harbor-bin:/work/harbor066/bin:/work/bin:/usr/local/bin:/usr/bin:/bin'
    jobs = Path(os.environ['BIOTASKS_SHARED_ROOT']) / 'jobs' / args.prefix
    jobs.mkdir(parents=True, exist_ok=True)
    try:
        for task in tasks:
            for agent in ['nop', 'oracle']:
                # A verifier can consume two 300-second attempts before setup/teardown.
                # Avoid beginning another trial with less than that time left.
                remaining = int(args.deadline - time.time() - 20)
                if remaining < 660:
                    return
                row = next(r for r in rows if r['task'] == task.name and r['agent'] == agent)
                name = task.name + '-' + agent
                command = ['/work/harbor066/bin/harbor', 'run', '-p', str(task), '-a', agent,
                           '--env', 'docker', '-n', '1', '-k', '1', '-r', '0',
                           '--override-cpus', '1', '--override-memory-mb', '6144',
                           '-o', str(jobs), '--job-name', name]
                row.update(command=command, started=time.time(), state='running')
                save()
                print('CONTROL_START ' + name, flush=True)
                try:
                    with (evidence / (args.prefix + '-' + name + '.log')).open('w') as log:
                        result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                                check=False, timeout=min(3300, remaining))
                    row.update(exit_code=result.returncode, state='completed', finished=time.time())
                except subprocess.TimeoutExpired:
                    row.update(state='deadline_censored', finished=time.time(),
                               reason='primary_control_allocation_or_trial_wrapper_deadline')
                    save()
                    return
                row['trial_results'] = []
                for path in sorted((jobs / name).glob('*/result.json')):
                    row['trial_results'].append({'path': str(path), 'result': json.loads(path.read_text())})
                for path in sorted((jobs / name).rglob('reward*')):
                    if path.is_file() and path.stat().st_size < 100000:
                        row.setdefault('reward_files', {})[str(path.relative_to(jobs / name))] = path.read_text()
                save()
                print('CONTROL_END ' + name + ' exit=' + str(result.returncode), flush=True)
    finally:
        after = {str(task): file_hashes(task) for task in tasks}
        (evidence / (args.prefix + '-task-files-unchanged.json')).write_text(json.dumps({
            'verified': before == after, 'before': before, 'after': after}, indent=2) + '\n')
        assert before == after, 'Harbor modified original task files'
        save()


if __name__ == '__main__':
    main()
