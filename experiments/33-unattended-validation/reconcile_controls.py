"""Reconcile recorded outcomes without regrading or conflating image variants."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def reconcile(baseline, followup):
    sources = {}
    def read(path, label):
        raw = path.read_bytes()
        sources[label] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    tasks = {}
    for path in sorted((baseline / 'results').glob('*.json')):
        data = read(path, '28/' + path.name)
        if not isinstance(data, dict) or 'task_controls' not in data:
            continue
        assert len(data['task_controls']) == data['native_exports_manifest_present']
        for task in data['task_controls']:
            name = task['task']
            assert name not in tasks, name
            base, oracle = (task['controls'][a] for a in ('nop', 'oracle'))
            positive = bool(all(r.get('task_files_unchanged') and r.get('reward_consistent')
                and r.get('original_grade_matches_raw_log') and r.get('exact_pinned_verifier')
                and not r.get('exception') and r.get('reward_details', {}).get('parse_status') == 'ok'
                for r in (base, oracle)) and base.get('reward') == 0 and oracle.get('reward') == 1)
            clean = bool(positive and oracle['reward_details'].get('command_resolved'))
            assert positive == task['raw_primary_verified']
            assert clean == task['strict_clean_verified']
            tasks[name] = dict(task=name, repo=data['repo'], original_phase_sha256=data['original_phase_sha256'],
                attempts=[dict(source='28/' + path.name, environment='original', positive_pair=positive,
                    clean_oracle_command=clean)], identity_status='original phase and task name; full content identity pending')
    plan = read(followup / 'control-plan.json', '29/control-plan.json')
    selected = {t['task']: t for r in plan['repositories'] for t in r['tasks']}
    for source in plan['sources']:
        file = (baseline.parent if source['path'].startswith('history-wide/') else baseline) / source['path']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == source['sha256']
    for slug in ('matchms', 'ohif', 'scanpy'):
        label = f'29/{slug}-control-results.json'
        data = read(followup / f'{slug}-control-results.json', label)
        assert data['task_files_unchanged']
        groups = {}
        for row in data['rows']:
            key = (row['task'], row.get('verifier_timeout_seconds', 300))
            assert row['agent'] not in groups.setdefault(key, {})
            groups[key][row['agent']] = row
        for (name, timeout), rows in groups.items():
            assert set(rows) == {'nop', 'oracle'} and name in tasks and name in selected
            base, oracle = rows['nop'], rows['oracle']
            positive = bool(all(r.get('state') == 'completed' and not r.get('exception')
                and r.get('parse_status') == 'ok' for r in (base, oracle))
                and base.get('reward') == 0 and oracle.get('reward') == 1
                and oracle.get('f2p_total', 0) > 0
                and oracle.get('f2p_passed') == oracle.get('f2p_total')
                and all(r.get('p2p_passed') == r.get('p2p_total') for r in (base, oracle)))
            clean = bool(positive and oracle.get('command_resolved') and oracle.get('test_exit_code') == 0)
            pair = next(p for p in data['pairs'] if p.get('task', name) == name and p.get('verifier_timeout_seconds', 300) == timeout)
            assert positive == pair['positive_control_pair'] and clean == pair['clean_oracle_command']
            tasks[name]['attempts'].append(dict(source=label, environment='reconstructed',
                verifier_timeout_seconds=timeout, positive_pair=positive, clean_oracle_command=clean,
                archive_sha256=data['archive_sha256']))
            files = selected[name]['original_files']
            tasks[name]['original_file_inventory_sha256'] = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    counts = Counter()
    for task in tasks.values():
        original = task['attempts'][0]
        task['ever_positive_pair'] = any(a['positive_pair'] for a in task['attempts'])
        task['ever_clean_oracle_command'] = any(a['clean_oracle_command'] for a in task['attempts'])
        counts['exports'] += 1
        counts['original_positive_pairs'] += original['positive_pair']
        counts['original_clean_commands'] += original['clean_oracle_command']
        counts['ever_positive_pairs'] += task['ever_positive_pair']
        counts['ever_clean_commands'] += task['ever_clean_oracle_command']
        counts['control_pair_attempts'] += len(task['attempts'])
    return dict(scope='Reconciliation of recorded #28 and #29 results; no new execution or raw-log regrading',
        counts=dict(counts), sources_sha256=sources, tasks=list(tasks.values()),
        limits=['Full base/head, task-content and image-digest identity reconciliation remains pending.',
            'Reconstructed environments may differ from original images.',
            'Ever-positive is evidence in at least one environment, not release readiness.',
            'The #31 MACS candidate is separate and excluded from the original export denominator.'])

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--followup', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = reconcile(args.baseline, args.followup)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['counts']))
