"""Read merged-PR totals for the original cohort without date filters or model calls."""

import datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parent
COHORT = ROOT.parent / 'cohort.json'


def main():
    cohort = json.loads(COHORT.read_text())
    fragments = []
    for index, row in enumerate(cohort):
        owner, name = row['repo'].split('/')
        fragments.append(
            f'r{index}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) '
            '{ nameWithOwner url isArchived '
            'defaultBranchRef { name target { oid } } '
            'pullRequests(states: MERGED) { totalCount } }'
        )
    query = 'query { ' + ' '.join(fragments) + ' rateLimit { cost remaining resetAt } }'
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    result = subprocess.run(
        ['gh', 'api', 'graphql', '-f', 'query=' + query],
        check=True, capture_output=True, text=True, timeout=90,
    )
    response = json.loads(result.stdout)
    assert not response.get('errors'), response.get('errors')
    rows = []
    for index, selected in enumerate(cohort):
        observed = response['data'][f'r{index}']
        assert observed['nameWithOwner'].lower() == selected['repo'].lower()
        rows.append({
            'repo': observed['nameWithOwner'],
            'field': selected['field_label'],
            'all_history_merged_count': observed['pullRequests']['totalCount'],
            'is_archived': observed['isArchived'],
            'default_branch_at_observation': observed['defaultBranchRef'],
            'previous_september_window_count': selected['window_count'],
        })
    output = {
        'started_utc': started,
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': time.monotonic() - clock,
        'method': 'One authenticated read-only GitHub GraphQL query, pullRequests(states: MERGED).totalCount, no date or PR-count filter.',
        'query': query,
        'cohort_sha256': hashlib.sha256(COHORT.read_bytes()).hexdigest(),
        'scope': 'Counts only, not a paginated inventory, eligibility assessment, execution or task yield. Counts may change after observation.',
        'estimated_peak_working_set_mib': 64,
        'self_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'proc_memory_high_water': next(line.strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmHWM:')),
        'child_peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'github_rate_limit': response['data']['rateLimit'],
        'openrouter_calls': 0,
        'repositories': rows,
        'total_merged_prs': sum(row['all_history_merged_count'] for row in rows),
    }
    (ROOT / 'history-counts.json').write_text(json.dumps(output, indent=2) + '\n')
    for row in rows:
        print(f"{row['repo']}: {row['all_history_merged_count']} merged PRs")
    print(f"Total: {output['total_merged_prs']}; model calls: 0")


if __name__ == '__main__':
    main()
