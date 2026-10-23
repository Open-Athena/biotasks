"""Derive pending controls and reconstruction identities from original evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-root', required=True, type=Path)
    args = parser.parse_args()
    baseline = args.baseline_root
    results = []
    sources = []
    for slug in ['matchms__matchms', 'OHIF__Viewers', 'scverse__scanpy']:
        source = baseline / 'results' / (slug + '.json')
        data = json.loads(source.read_text())
        sources.append({'path': 'history-wide/results/' + source.name, 'sha256': sha(source)})
        pending = [r for r in data['original_control_allocation'] if r['state'] != 'completed']
        selected = sorted({r['task'] for r in pending})
        if slug == 'scverse__scanpy':
            selected = ['scverse__scanpy-4389']
        manifest_path = baseline / 'archives' / (slug + '-manifest.json')
        if slug == 'matchms__matchms':
            manifest_path = baseline / 'archives/drafts/matchms__matchms-unpublished-private-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        sources.append({'path': str(manifest_path.relative_to(baseline)), 'sha256': sha(manifest_path)})
        phase = next(f for f in manifest['files'] if f['path'].endswith('phase-artifacts.tar.gz'))
        members = phase['members']
        setup = [m for m in members if m['path'].startswith('bootstrap/') and m['path'].endswith(('bootstrap.json', 'Dockerfile'))]
        records = []
        for task in selected:
            controls = next(r['controls'] for r in data['task_controls'] if r['task'] == task)
            identity = [m for m in members if m['path'].startswith('outputs/' + slug + '/' + task + '/')]
            assert identity, task
            records.append({'task': task, 'original_controls': {
                agent: {'exception': controls.get(agent, {}).get('exception'),
                        'reward': controls.get(agent, {}).get('reward'),
                        'state': next(r['state'] for r in data['original_control_allocation'] if r['task'] == task and r['agent'] == agent)}
                for agent in ['nop', 'oracle']}, 'original_files': identity,
                'proposed_arms_seconds': [300, 1200] if slug == 'scverse__scanpy' else [300],
                'run_both_controls_per_arm': True})
        results.append({'repo': data['repo'], 'slug': slug,
                        'unstarted': [{'task': r['task'], 'agent': r['agent'], 'state': r['state']} for r in pending],
                        'tasks': records, 'reconstruction_records': setup,
                        'original_phase': {k: phase[k] for k in ['path', 'sha256', 'bytes']},
                        'retention': 'protected local originals; public curated archive is insufficient' if slug == 'matchms__matchms' else 'verified public full-original archive'})
    total = sum(len(r['unstarted']) for r in results)
    assert total == 14
    commands = sum(len(t['proposed_arms_seconds']) * 2 for r in results for t in r['tasks'])
    assert commands == 20
    report = {'scope': 'Input/scheduling plan only; no task rebuilt or executed', 'sources': sources,
              'original_unstarted_commands': total, 'proposed_control_commands': commands,
              'why_more_than_unstarted': 'Two partly completed pairs need both controls on the reconstructed image (16 scheduling commands); Scanpy needs two arms with both controls (4 more).',
              'repositories': results}
    (ROOT / 'control-plan.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'unstarted': total, 'proposed_commands': commands, 'tasks': {r['repo']: [t['task'] for t in r['tasks']] for r in results}}, indent=2))

if __name__ == '__main__':
    main()
