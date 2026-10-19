"""Project bounded worker lifecycle records without copying private configuration."""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path


def inventory(root):
    records = {}
    conflicts = []
    with subprocess.Popen(['rg', '--files', str(root)], stdout=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            path = Path(line.strip())
            if path.parent.name != 'workers' or path.suffix != '.json':
                continue
            assert path.stat().st_size < 1024 * 1024
            raw = path.read_bytes()
            data = json.loads(raw)
            if not isinstance(data, dict) or 'worker_id' not in data:
                continue
            spec = data.get('spec', {})
            row = {k: data.get(k) for k in ('worker_id', 'state', 'started_at', 'stopped_at')}
            row['resources'] = {k: spec.get(k) for k in ('provider', 'cpus', 'memory_mb', 'disk_gb')}
            row['worker_name'] = spec.get('name')
            source = {'relative_local_evidence_path': str(path.relative_to(root)),
                      'original_sha256': hashlib.sha256(raw).hexdigest()}
            identity = row['worker_id']
            if identity in records:
                previous = {k: v for k, v in records[identity].items() if k != 'sources'}
                if previous != row:
                    conflicts.append({'worker_id': identity, 'other_projection': row, 'source': source})
                else:
                    records[identity]['sources'].append(source)
            else:
                records[identity] = {**row, 'sources': [source]}
        assert proc.wait() == 0
    for row in records.values():
        assert row['state'] == 'terminated' and row['started_at'] and row['stopped_at']
        seconds = (datetime.datetime.fromisoformat(row['stopped_at']) - datetime.datetime.fromisoformat(row['started_at'])).total_seconds()
        assert seconds >= 0
        row['recorded_lifetime_seconds'] = seconds
    return {'recorded_sandbox_hours': sum(x['recorded_lifetime_seconds'] for x in records.values()) / 3600,
            'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'stage': 'lifecycle_inventory_pending_route_attribution_and_completeness_audit',
            'unique_worker_ids': len(records), 'workers': list(records.values()),
            'conflicting_observations': conflicts,
            'limitations': ['Local retained records are not a complete provider billing export.',
                           'Duplicates are deduplicated by exact sandbox ID; conflicts are retained.',
                           'Route and generation/validation/solver/Marin attribution is not inferred from names.',
                           'No invoice total or full per-accepted-task cost is established.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.private_root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'workers': result['unique_worker_ids'],
                      'conflicting_observations': len(result['conflicting_observations'])}))
