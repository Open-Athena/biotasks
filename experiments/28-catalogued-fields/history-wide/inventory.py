"""Enumerate merged PR metadata with stable cursors, a frozen cutoff and no models."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
QUERY = '''query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    pullRequests(states: MERGED, first: 100, after: $cursor,
                 orderBy: {field: CREATED_AT, direction: ASC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { id number title url createdAt mergedAt baseRefName baseRefOid headRefOid }
    }
  }
  rateLimit { cost remaining resetAt }
}'''


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def stamp(value):
    return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))


def node_safety():
    available = int(next(row.split()[1] for row in Path('/proc/meminfo').read_text().splitlines()
                         if row.startswith('MemAvailable:'))) * 1024
    assert available >= 2 * 1024**3 and os.getloadavg()[0] <= 2.5, 'Shared node contention; checkpoint retained'


def inspect_page(page, repo, cursor, cutoff, seen):
    assert not page.get('errors'), page.get('errors')
    repository = page['data']['repository']
    assert repository['nameWithOwner'].lower() == repo.lower()
    connection = repository['pullRequests']
    info = connection['pageInfo']
    assert not info['hasNextPage'] or (info['endCursor'] and info['endCursor'] != cursor)
    assert connection['nodes'] or not info['hasNextPage']
    accepted, later = [], 0
    for row in connection['nodes']:
        assert row['mergedAt'] and row['createdAt'] and isinstance(row['number'], int)
        if stamp(row['mergedAt']) > cutoff:
            later += 1
            continue
        assert row['number'] not in seen, 'Duplicate PR across cursor pages'
        seen.add(row['number'])
        accepted.append(row)
    return connection, accepted, later


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, default=ROOT)
    parser.add_argument('--remote-worker', action='store_true')
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    if args.remote_worker:
        assert os.environ.get('IRIS_OUTPUT_DIR') and os.environ.get('GH_TOKEN')
    counts = read(ROOT / 'history-counts.json')
    cutoff = stamp(counts['finished_utc'])
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    report = {'started_utc': started, 'cutoff_utc': cutoff.isoformat(),
        'method': 'Serial GraphQL merged-PR cursor traversal in createdAt ascending order, no lower date cutoff or total PR limit. Only mergedAt<=frozen cutoff enters inventory. Original count and unique PR identities must agree.',
        'scope': 'Metadata inventory, not eligibility, native acquisition/validation, task export or a success denominator.',
        'source_sha256': sha(Path(__file__)), 'count_source_sha256': sha(ROOT / 'history-counts.json'),
        'query': QUERY, 'estimated_peak_working_set_mib': 128,
        'model_calls': 0, 'repositories': []}
    for selected in counts['repositories']:
        repo = selected['repo']; owner, name = repo.split('/')
        directory = args.state_dir / repo.replace('/', '__')
        directory.mkdir(exist_ok=True)
        cursor, seen, page_index = None, set(), 0
        later, pages, previous_created = 0, [], None
        output = directory / 'inventory.jsonl'
        # Rebuild bounded inventory from saved original pages on resumption.
        with output.open('w') as inventory:
            while True:
                if not args.remote_worker:
                    node_safety()
                path = directory / f'page-{page_index:04d}.json'
                if path.exists():
                    page = read(path)
                else:
                    if args.remote_worker:
                        request = urllib.request.Request('https://api.github.com/graphql',
                            data=json.dumps({'query': QUERY, 'variables': {
                                'owner': owner, 'name': name, 'cursor': cursor}}).encode(),
                            headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                                'User-Agent': 'BioTasks-history-metadata',
                                'Content-Type': 'application/json'})
                        with urllib.request.urlopen(request, timeout=60) as response:
                            body = response.read(2 * 1024**2 + 1)
                        assert len(body) <= 2 * 1024**2
                        page = json.loads(body)
                    else:
                        command = ['gh', 'api', 'graphql', '-f', 'query=' + QUERY,
                            '-f', 'owner=' + owner, '-f', 'name=' + name]
                        if cursor is not None:
                            command += ['-f', 'cursor=' + cursor]
                        response = subprocess.run(command, capture_output=True, text=True,
                            check=True, timeout=60)
                        assert len(response.stdout.encode()) <= 2 * 1024**2
                        page = json.loads(response.stdout)
                    assert not page.get('errors'), page.get('errors')
                    save(path, page)
                connection, accepted, excluded = inspect_page(page, repo, cursor, cutoff, seen)
                later += excluded
                for row in accepted:
                    created = stamp(row['createdAt'])
                    assert previous_created is None or created >= previous_created
                    previous_created = created
                    inventory.write(json.dumps(row, sort_keys=True) + '\n')
                pages.append({'path': str(path.relative_to(args.state_dir)),
                    'sha256': sha(path), 'bytes': path.stat().st_size,
                    'request_cursor': cursor, 'end_cursor': connection['pageInfo']['endCursor'],
                    'has_next_page': connection['pageInfo']['hasNextPage'],
                    'observed_total_count': connection['totalCount']})
                if not connection['pageInfo']['hasNextPage']:
                    break
                cursor = connection['pageInfo']['endCursor']
                page_index += 1
        assert len(seen) == selected['all_history_merged_count'], (
            repo, len(seen), selected['all_history_merged_count'], 'Frozen count mismatch; do not declare complete')
        row = {'repo': repo, 'unique_merged_prs_at_cutoff': len(seen),
            'original_count_matches': True, 'cursor_exhausted': True,
            'post_cutoff_merges_excluded': later, 'pages': pages,
            'inventory': {'path': str(output.relative_to(args.state_dir)),
                'sha256': sha(output), 'bytes': output.stat().st_size}}
        report['repositories'].append(row)
        save(args.report_dir / 'inventory-progress.json', report)
        print(json.dumps({'repo': repo, 'unique_merged_prs': len(seen), 'pages': len(pages),
            'cutoff_count_matches': True, 'remaining_github_points': page['data']['rateLimit']['remaining']}), flush=True)
    report.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        elapsed_seconds=time.monotonic() - clock,
        proc_memory_high_water=next(line.strip() for line in Path('/proc/self/status').read_text().splitlines()
            if line.startswith('VmHWM:')),
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        full_history_enumeration_complete=len(report['repositories']) == 10,
        unique_merged_prs=sum(r['unique_merged_prs_at_cutoff'] for r in report['repositories']))
    assert report['unique_merged_prs'] == counts['total_merged_prs']
    save(args.report_dir / 'inventory-manifest.json', report)
    print(json.dumps({key: value for key, value in report.items() if key not in ['repositories', 'query']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
