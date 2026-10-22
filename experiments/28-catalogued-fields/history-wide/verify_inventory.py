"""Verify original saved cursor pages/inventories without network access or reruns."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

from inventory import inspect_page, read, sha, stamp

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    report = read(args.state_dir / 'inventory-progress.json')
    counts = read(ROOT / 'history-counts.json')
    assert len(report['repositories']) == len(counts['repositories']) == 10
    assert report['count_source_sha256'] == sha(ROOT / 'history-counts.json')
    cutoff = stamp(report['cutoff_utc'])
    assert cutoff == stamp(counts['finished_utc'])
    verified = []
    for record, selected in zip(report['repositories'], counts['repositories']):
        assert record['repo'] == selected['repo']
        cursor, seen, numbers, last_created = None, set(), [], None
        digest = hashlib.sha256()
        rows_bytes, later = 0, 0
        for index, original in enumerate(record['pages']):
            path = args.state_dir / 'pages' / original['path']
            assert path.stat().st_size == original['bytes'] and sha(path) == original['sha256']
            assert original['request_cursor'] == cursor
            page = read(path)
            connection, accepted, excluded = inspect_page(page, selected['repo'], cursor, cutoff, seen)
            info = connection['pageInfo']
            assert info['hasNextPage'] == (index < len(record['pages']) - 1)
            assert info['endCursor'] == original['end_cursor']
            cursor = info['endCursor']
            later += excluded
            for row in accepted:
                created = stamp(row['createdAt'])
                assert last_created is None or created >= last_created
                last_created = created
                data = (json.dumps(row, sort_keys=True) + '\n').encode()
                digest.update(data); rows_bytes += len(data); numbers.append(row['number'])
        assert len(seen) == selected['all_history_merged_count'] == record['unique_merged_prs_at_cutoff']
        inventory = args.state_dir / 'pages' / record['inventory']['path']
        assert rows_bytes == inventory.stat().st_size == record['inventory']['bytes']
        assert digest.hexdigest() == sha(inventory) == record['inventory']['sha256']
        ordered = list(reversed(numbers))  # bounded IDs only; no eager data sort
        ids = {'repo': selected['repo'], 'cutoff_utc': report['cutoff_utc'],
            'order': 'createdAt descending; exact reverse of original cursor inventory',
            'source_inventory_sha256': digest.hexdigest(), 'pr_numbers': ordered}
        inputs = ROOT / 'candidate-identities'; inputs.mkdir(exist_ok=True)
        target = inputs / (selected['repo'].replace('/', '__') + '.json')
        target.write_text(json.dumps(ids, indent=2) + '\n')
        verified.append({'repo': selected['repo'], 'unique_merged_prs_at_cutoff': len(seen),
            'cursor_exhausted': True, 'pages': len(record['pages']),
            'post_cutoff_merges_excluded': later, 'all_page_sha256_and_inventory_bytes_match': True,
            'candidate_id_file': str(target.relative_to(ROOT)), 'candidate_id_sha256': sha(target),
            'source_inventory_sha256': digest.hexdigest()})
    result = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'method': 'Offline independent reconciliation of all original cursor edges, per-page SHA256/size, unique PR identities, frozen merge cutoff, counts and canonical inventory bytes. No network, models or repeated enumeration.',
        'source_job': '/exedev/biotasks28-history-inventory-001',
        'original_job_state': 'FAILED',
        'original_failure': 'All ten repo traversals completed; final optional VmHWM telemetry read raised StopIteration under gVisor. Original pages/progress retained unchanged.',
        'remote_memory_high_water': None,
        'full_history_enumeration_complete': True,
        'unique_merged_prs': sum(row['unique_merged_prs_at_cutoff'] for row in verified),
        'page_count': sum(row['pages'] for row in verified),
        'original_progress_sha256': sha(args.state_dir / 'inventory-progress.json'),
        'model_calls': 0, 'native_validation_started': False, 'repositories': verified}
    assert result['unique_merged_prs'] == counts['total_merged_prs']
    (ROOT / 'inventory-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
