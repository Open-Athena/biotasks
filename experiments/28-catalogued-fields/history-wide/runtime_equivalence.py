"""Audit exact retained execution bytes and tracked-test counts; no semantic deduplication."""

import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    assert args.slug in {r['slug'] for r in read(ROOT.parent / 'cohort.json')}
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    source = args.state_dir / (run + '-results')
    inventory_path = source / 'fresh-task-files-unchanged.json'
    inventory = read(inventory_path)
    assert inventory['verified'] and inventory['before'] == inventory['after']
    assessment_path = ROOT / 'results' / (args.slug + '.json')
    assessment = read(assessment_path)
    phase = source / 'phase-artifacts.tar.gz'
    assert sha(phase.read_bytes()) == assessment['original_phase_sha256']
    originals, expanded, output_bytes = {}, 0, 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            expanded += member.size
            assert expanded <= 32 * 1024**2
            if member.name.startswith('outputs/'):
                output_bytes += member.size
                assert output_bytes <= 16 * 1024**2 and member.size < 1024**2
                assert member.name not in originals
                originals[member.name] = archive.extractfile(member).read()
    tasks = {r['task']: r for r in assessment['task_controls']}
    groups, tracked_counts = defaultdict(list), Counter()
    key_fields = set()
    for original, files in inventory['before'].items():
        path = Path(original).relative_to('/work')
        assert path.name in tasks
        assert set(files) == {'instruction.md', 'task.toml', 'solution/patch.diff', 'solution/solve.sh',
            'tests/verifier.py', 'tests/p2p.json', 'tests/f2p.json', 'tests/test.sh',
            'environment/Dockerfile', 'environment/docker-compose.yaml'}
        key = {}
        for name, expected in files.items():
            raw = originals[(path / name).as_posix()]
            assert len(raw) < 1024**2 and sha(raw) == expected
            if name not in ['instruction.md', 'task.toml']:
                key[name] = expected
        config = tomllib.loads(originals[(path / 'task.toml').as_posix()].decode())
        assert set(config) == {'version', 'task', 'metadata', 'agent', 'verifier'}
        # Only descriptive identity/title and freeform provenance metadata are excluded.
        task_settings = {k: v for k, v in config['task'].items() if k not in ['name', 'description']}
        key['task_execution_settings'] = {**{k: v for k, v in config.items() if k not in ['task', 'metadata']},
            'task': task_settings}
        encoded = json.dumps(key, sort_keys=True, separators=(',', ':')).encode()
        groups[sha(encoded)].append({'task': path.name, 'instruction_sha256': files['instruction.md'],
            'primary_verified': tasks[path.name]['raw_primary_verified'],
            'clean_verified': tasks[path.name]['strict_clean_verified']})
        key_fields.update(key)
        f2p, p2p = (json.loads(originals[(path / name).as_posix()]) for name in ['tests/f2p.json', 'tests/p2p.json'])
        assert isinstance(f2p, list) and isinstance(p2p, list) and len(f2p) > 0
        assert len(set(f2p)) == len(f2p) and len(set(p2p)) == len(p2p) and not set(f2p) & set(p2p)
        tracked_counts[(len(f2p), len(p2p))] += 1
        for control in tasks[path.name]['controls'].values():
            details = control.get('reward_details')
            if details:
                assert details['f2p_total'] == len(f2p) and details['p2p_total'] == len(p2p)
    assert len(tasks) == sum(len(rows) for rows in groups.values())
    duplicates = [{'runtime_key_sha256': digest, 'tasks': rows,
        'instruction_bytes_equal': len({r['instruction_sha256'] for r in rows}) == 1}
        for digest, rows in sorted(groups.items()) if len(rows) > 1]
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Exact runtime-file/config byte equivalence and F2P/P2P inventory only. Not semantic deduplication, biological validity, solver difficulty or public-data clearance. Original counts/tasks/rewards unchanged.',
        'source_sha256': sha(Path(__file__).read_bytes()), 'task_count': len(tasks),
        'runtime_equivalence_groups': len(groups), 'duplicate_runtime_groups': duplicates,
        'key_fields': sorted(key_fields),
        'excluded_from_key': ['instruction.md (hash equality recorded separately)', 'task.toml metadata',
            'task.toml task.name', 'task.toml task.description'],
        'tracked_test_count_distribution': [{'f2p': f2p, 'p2p': p2p, 'packages': n}
            for (f2p, p2p), n in sorted(tracked_counts.items())],
        'source_task_hash_inventory_sha256': sha(inventory_path.read_bytes()),
        'source_assessment_sha256': sha(assessment_path.read_bytes()),
        'all_original_task_files_unchanged': True,
        'runtime_groups_with_primary_success': sum(any(r['primary_verified'] for r in rows) for rows in groups.values()),
        'runtime_groups_with_clean_success': sum(any(r['clean_verified'] for r in rows) for rows in groups.values())}
    target = ROOT / 'results' / (args.slug + '-full-runtime-equivalence.json')
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['tracked_test_count_distribution', 'duplicate_runtime_groups']}))
    print(json.dumps({'duplicate_runtime_groups': duplicates}))


if __name__ == '__main__':
    main()
