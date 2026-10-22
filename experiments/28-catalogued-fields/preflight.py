"""Read-only cohort accounting; never changes upstream candidate selection."""

import datetime
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def main():
    metadata = json.loads((ROOT / 'preflight/pinned-repositories.json').read_text())['data']
    selection = json.loads((ROOT / 'selection.json').read_text())
    cohort = []
    for index, row in enumerate(selection['selected']):
        repository = metadata['r' + str(index)]
        name = repository['nameWithOwner']
        assert name.lower() == row['repo'].lower() and not repository['isArchived']
        slug = name.replace('/', '__')
        ref = repository['defaultBranchRef']['target']['oid']
        assert len(ref) == 40
        (ROOT / 'preflight' / (slug + '-repository.json')).write_text(json.dumps(repository, indent=2) + '\n')
        records = {}
        for kind, extra in [('window', ['--search', 'merged:2026-09-01..2026-09-30', '--limit', '1000']),
                            ('newest300', ['--limit', '300'])]:
            command = ['gh', 'pr', 'list', '--repo', name, '--state', 'merged', *extra,
                       '--json', 'number,title,mergedAt,isDraft,url,labels']
            response = subprocess.run(command, capture_output=True, text=True, check=True, timeout=180)
            records[kind] = json.loads(response.stdout)
            (ROOT / 'preflight' / (slug + '-' + kind + '.json')).write_text(json.dumps(records[kind], indent=2) + '\n')
        assert len(records['window']) < 1000, 'Window exceeded independent accounting cap'
        window_numbers = {r['number'] for r in records['window']}
        in_window = [r for r in records['newest300']
                     if not r['isDraft'] and r.get('mergedAt')
                     and '2026-09-01' <= r['mergedAt'][:10] <= '2026-09-30']
        entry = {
            'repo': name, 'slug': slug, 'ref': ref,
            'scientific_field_slot': row['coverage_slot'], 'field_label': row['field_label'],
            'catalog_labels': row['catalog_field_labels'], 'catalog_review': row['catalog_review'],
            'window_count': len(records['window']), 'newest300_window_count': len(in_window),
            'expected_native_limit': 100,
            'expected_native_candidate_numbers_before_base_lookup': [r['number'] for r in in_window[:100]],
            'omitted_by_newest300': sorted(window_numbers - {r['number'] for r in in_window}),
            'limitation': 'Native base-SHA lookup can omit PRs; compare actual returned candidates at run time. Independent lists contain metadata only.',
            'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        cohort.append(entry)
        (ROOT / 'cohort.json').write_text(json.dumps(cohort, indent=2) + '\n')
        config = {
            'repo': {'url': 'https://github.com/' + name, 'ref': ref, 'access': 'public'},
            'pipeline': {'name': 'pr_runtime', 'options': {'limit': 100, 'since': '2026-09-01', 'until': '2026-09-30'}},
            'llm': {'provider': 'openrouter', 'model': 'anthropic/claude-sonnet-4.6',
                    'api_key_env': 'OPENROUTER_API_KEY', 'fallback': None},
            'bootstrap': {'max_iterations': 20, 'max_seconds': 1800,
                          'max_llm_spend_usd': 5.0, 'cache_dir': '/work/bootstrap'},
            'auth': {'use_gh_cli': False, 'use_hf_cli': False},
            'output': {'destination': '/work/outputs/' + slug, 'org': 'open-athena',
                       'dataset_name': 'biotasks28-catalogued-fields', 'visibility': 'private'},
        }
        (ROOT / 'native-configs' / (slug + '.json')).write_text(json.dumps(config, indent=2) + '\n')
        print(name, 'window=' + str(entry['window_count']),
              'newest300_window=' + str(len(in_window)),
              'native_upper_bound=' + str(min(100, len(in_window))), flush=True)


if __name__ == '__main__':
    main()
