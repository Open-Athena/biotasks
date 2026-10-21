"""Read original run evidence; never alter tasks, rewards or native outcomes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import tarfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    expanded = args.results / 'expanded'
    expanded.mkdir(exist_ok=True)
    total = 0
    with tarfile.open(args.results / 'phase-artifacts.tar.gz') as archive:
        for member in archive:
            if member.isdir(): continue
            relative = Path(member.name)
            assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
            assert member.size < 20 * 1024**2
            total += member.size
            assert total < 200 * 1024**2
            target = expanded / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    report = {'expanded_bytes': total, 'bootstrap': [], 'native_logs': [], 'tasks': []}
    for path in sorted((expanded / 'bootstrap').rglob('bootstrap.json')):
        row = json.loads(path.read_text())
        report['bootstrap'].append({k: row.get(k) for k in ['repo','ref','iterations','build_time_sec',
            'smoke_passed','verify_passed','verify_detail','llm_cost_estimate_usd','rebuild_cmds','test_cmds']})
    for path in sorted(args.results.glob('*__*.log')):
        if path.name.startswith('fresh-'): continue
        text = path.read_text(errors='replace')
        actions = Counter(re.findall(r'step=\d+ action=(\w+)', text))
        report['native_logs'].append({'file':path.name,'actions':dict(actions),
            'candidates':re.findall(r'candidates\s+(\d+)',text),
            'emitted':re.findall(r'emitted\s+(\d+)',text),
            'skipped':re.findall(r'skipped\s+(\d+)',text)})
    controls_path = args.results / 'fresh-controls.json'
    controls = json.loads(controls_path.read_text()) if controls_path.exists() else []
    for path in sorted((expanded / 'outputs').rglob('task.toml')):
        task = path.parent
        row = {'task':task.name,'path':str(task.relative_to(expanded)), 'controls':{}}
        for name in ['f2p','p2p']:
            ids = json.loads((task/'tests'/(name+'.json')).read_text())
            row[name+'_count'] = len(ids)
        for control in controls:
            if control['task'] != task.name: continue
            details = [json.loads(v) for k,v in control.get('reward_files',{}).items()
                       if k.endswith('reward-details.json')]
            row['controls'][control['agent']] = {'state':control.get('state'),
                'exit_code':control.get('exit_code'),'details':details,
                'exceptions':[r['result'].get('exception_info') for r in control.get('trial_results',[])]}
        base = row['controls'].get('nop',{}).get('details',[])
        oracle = row['controls'].get('oracle',{}).get('details',[])
        row['verified'] = bool(len(base)==1 and len(oracle)==1 and base[0].get('reward')==0
            and oracle[0].get('reward')==1 and base[0].get('parse_status')=='ok'
            and oracle[0].get('parse_status')=='ok')
        row['oracle_command_resolved'] = bool(oracle and oracle[0].get('command_resolved'))
        report['tasks'].append(row)
    report['exported_count'] = len(report['tasks'])
    report['independently_verified_count'] = sum(t['verified'] for t in report['tasks'])
    report['strict_oracle_count'] = sum(t['verified'] and t['oracle_command_resolved'] for t in report['tasks'])
    (args.results/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
