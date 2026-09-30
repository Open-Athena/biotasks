import datetime
import hashlib
import itertools
import json
import os
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

ROOT = Path('/tmp/bio-discovery-20260929')
CACHE = ROOT / 'adoption'
INVENTORY = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments/bio-repository-inventory.json')
START = '2026-08-30'
END = '2026-09-28'


def resources(start=False):
    mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    load = os.getloadavg()[0]
    if start:
        assert mem >= 2.5 * 1024**3 and mem - 200 * 1024**2 >= 2 * 1024**3 and load < 1.5, (mem, load)
    elif mem < 2 * 1024**3 or load > 2.5:
        raise RuntimeError(f'Node resource threshold: {mem=}, {load=}')


def pair_result(records, x_key, y_key):
    rows = [r for r in records if r['adoption_metrics'].get(x_key) is not None and r['adoption_metrics'].get(y_key) is not None]
    result = {'x': x_key, 'y': y_key, 'n': len(rows), 'members': [r['name'] for r in rows]}
    if len(rows) < 3:
        return dict(result, spearman_rho=None, pearson_raw_r=None, pearson_log1p_r=None)
    x = np.array([r['adoption_metrics'][x_key] for r in rows], dtype=float)
    y = np.array([r['adoption_metrics'][y_key] for r in rows], dtype=float)
    return dict(result, spearman_rho=float(spearmanr(x, y).statistic), pearson_raw_r=float(pearsonr(x, y).statistic), pearson_log1p_r=float(pearsonr(np.log10(1+x), np.log10(1+y)).statistic))


resources(start=True)
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated peak 200 MiB', flush=True)
data = json.loads(INVENTORY.read_text())
assert len(data['candidates']) == 95
records = data['candidates']
by_name = {r['name']: r for r in records}
for row in json.loads((CACHE / 'github-mappings.json').read_text()):
    record = by_name[row['name']]
    record['github_metadata'] = row['metadata']
    record['github_mapping_evidence'] = {
        'source_url': 'https://bioconductor.org/packages/3.23/bioc/VIEWS',
        'package_fields': row['mapping_evidence'],
        'method': 'GitHub repository linked by release package URL or BugReports; stars taken from that repository, not an arbitrary mirror.',
    }

mappings = json.loads((CACHE / 'pypi-mappings.json').read_text())
quast_meta = json.loads((CACHE / 'quast.pypi.json').read_text())['info']
mappings.append({'name': 'QUAST', 'package': 'quast', 'metadata': {k:quast_meta.get(k) for k in ('name', 'version', 'summary', 'home_page', 'project_urls', 'license', 'requires_python')}, 'stats_status': 200})
for record in records:
    record['pypi_packages'] = []
    record['pypi_mapping_status'] = 'No verified PyPI distribution identified in package metadata screening; missing is not zero.'
    if not record.get('github_metadata'):
        record['github_metric_status'] = 'No upstream GitHub mapping verified in this pass; missing is not zero.'
    else:
        record['github_metric_status'] = 'Measured on the package-linked GitHub repository.'

for row in mappings:
    assert row['stats_status'] == 200, row
    record = by_name[row['name']]
    package = row['package'].lower()
    payload = (CACHE / f'{package}.overall.json').read_bytes()
    stats = json.loads(payload)
    assert stats['package'].lower() == package
    days = [d for d in stats['data'] if START <= d['date'] <= END and d['category'] == 'without_mirrors']
    expected_days = [(datetime.date.fromisoformat(START) + datetime.timedelta(days=i)).isoformat() for i in range(30)]
    assert sorted(d['date'] for d in days) == expected_days, package
    assert all(isinstance(d['downloads'], int) and d['downloads'] >= 0 for d in days)
    source_url = f'https://pypistats.org/api/packages/{package}/overall?mirrors=false'
    source_repo = record['repository_url'].replace('https://', '').lower().rstrip('/')
    identity = json.dumps(row['metadata']).replace('https://', '').replace('http://', '').lower()
    if row['name'] == 'CheckM':
        evidence = {'url': 'https://github.com/Ecogenomics/CheckM/wiki/Installation', 'observation': 'Official repository installation instructions name pip package checkm-genome; PyPI description links Ecogenomics/CheckM.'}
    elif row['name'] == 'QUAST':
        evidence = {'url': 'https://github.com/ablab/quast', 'observation': 'Repository links quast.sf.net as official homepage; PyPI metadata identifies the same homepage and genome assembly evaluation purpose.'}
    else:
        assert source_repo in identity, (row['name'], source_repo, identity)
        evidence = {'url': f'https://pypi.org/pypi/{package}/json', 'observation': 'PyPI project URLs link the inventoried GitHub repository.'}
    recent90 = [d for d in stats['data'] if '2026-07-01' <= d['date'] <= END and d['category'] == 'without_mirrors']
    assert len(recent90) == 90 and len({d['date'] for d in recent90}) == 90
    record['pypi_packages'].append({
        'name': stats['package'], 'metadata': row['metadata'], 'identity_evidence': evidence,
        'metadata_url': f'https://pypi.org/pypi/{package}/json',
        'download_source': source_url, 'observed_on': '2026-09-29',
        'window_start': START, 'window_end': END, 'window_days': 30,
        'mirror_policy': 'without_mirrors; provider excludes known mirrors',
        'downloads_30d': sum(d['downloads'] for d in days),
        'daily_downloads': [{'date': d['date'], 'downloads': d['downloads']} for d in days],
        'downloads_90d': sum(d['downloads'] for d in recent90),
        'window_90d_start': '2026-07-01',
        'daily_downloads_90d': [{'date': d['date'], 'downloads': d['downloads']} for d in recent90],
        'download_response_sha256': hashlib.sha256(payload).hexdigest(),
    })
    record['pypi_mapping_status'] = 'Verified using upstream installation documentation or matching package source URLs.'

by_name['SEPP']['pypi_mapping_status'] = 'Rejected PyPI sepp: metadata identifies Science Exploitation and Preservation Platform at ESA, unrelated to phylogenetic placement.'
by_name['SEPP']['pypi_rejected_mapping'] = {'metadata_url': 'https://pypi.org/pypi/sepp/json', 'summary': 'Science Exploitation and Preservation Platform', 'repository': 'https://repos.cosmos.esa.int/socci/projects/SEPP/repos/sepp', 'observed_on': '2026-09-29'}
for name in ['BUSCO', 'SPAdes']:
    by_name[name]['pypi_mapping_status'] = f'PyPI /pypi/{name.lower()}/json returned HTTP 404 on 2026-09-29; no alternate official PyPI name verified.'

for r in records:
    b = [p['cumulative_downloads'] for p in r['bioconda_packages']]
    p30 = [p['downloads_30d'] for p in r['pypi_packages']]
    p90 = [p['downloads_90d'] for p in r['pypi_packages']]
    r['adoption_metrics'] = {
        'bioconda_max_package_downloads': max(b) if b else None,
        'bioconductor_download_score': r['bioconductor_download_score'],
        'github_stars': r.get('github_metadata', {}).get('stargazers_count'),
        'pypi_max_package_downloads_30d': max(p30) if p30 else None,
        'bioconda_sum_package_downloads': sum(b) if b else None,
        'pypi_sum_package_downloads_30d': sum(p30) if p30 else None,
        'pypi_max_package_downloads_90d': max(p90) if p90 else None,
    }

keys = ['bioconda_max_package_downloads', 'bioconductor_download_score', 'github_stars', 'pypi_max_package_downloads_30d']
pairs = [pair_result(records, x, y) for x, y in itertools.combinations(keys, 2)]
single = [r for r in records if len(r['bioconda_packages']) <= 1 and len(r['pypi_packages']) <= 1]
non_libraries = [r for r in records if r['role'] != 'scientific library']
data['adoption_analysis'] = {
    'observed_on': '2026-09-29', 'candidate_count': len(records),
    'selection': 'Existing 95 manually screened candidates held fixed; no new candidates or subdomain-targeted selection for this analysis.',
    'primary_statistic': 'Spearman correlation (Pearson correlation of average ranks for ties), pairwise complete observations.',
    'secondary_statistics': 'Pearson correlation on raw counts and log10(1 + count).',
    'package_aggregation': 'Maximum recorded package counter per software entry and registry. This is a proxy, not a download total or estimate of unique users; individual counters retained.',
    'missing_data': 'Exclude missing measurements separately for each pair; never replace missing values with zero.',
    'pypi_window': {'start': START, 'end': END, 'days': 30, 'timezone': 'UTC', 'known_mirrors': 'excluded by PyPIStats'},
    'coverage': {key: sum(r['adoption_metrics'][key] is not None for r in records) for key in keys},
    'pairs': pairs,
    'sensitivity_single_package_entries': [pair_result(single, x, y) for x, y in itertools.combinations(keys, 2)],
    'sensitivity_excluding_scientific_libraries': [pair_result(non_libraries, x, y) for x, y in itertools.combinations(keys, 2)],
    'sensitivity_summed_package_counters': [pair_result(records, x, y) for x, y in itertools.combinations(['bioconda_sum_package_downloads', 'bioconductor_download_score', 'github_stars', 'pypi_sum_package_downloads_30d'], 2)],
    'sensitivity_pypi_90d': [pair_result(records, x, 'pypi_max_package_downloads_90d') for x in keys[:3]],
    'limitations': [
        'The inventory was manually selected from adoption screens; these descriptive correlations do not estimate correlations across all biology software.',
        'The initial review displayed the top 110 package rows from each of Bioconda and Bioconductor, then selected candidates and adjacent tools manually. The 95 entries are not a statistical sample or a strict top-95 ranking.',
        'Bioconda is cumulative; Bioconductor averages monthly distinct IPs over September 2025 through August 2026; PyPI uses a recent 30-day window; stars measure repository interest at observation time.',
        'Downloads include dependencies and automation; caching and distribution channels affect counts. Stars are not an installation or research usage count.',
        'PyPI and Bioconductor pairs have no overlapping measured candidates in this inventory; absence of correlation estimates is not evidence of independence.',
        'GitHub counts attach to identified upstream repositories; other hosts and unresolved GitHub mappings remain missing, not zero.',
        'PyPI discovery checked metadata and Python-based candidates; no claim of an exhaustive search for alternate package names or wrappers.',
        'No observed adoption metric establishes biological task quality, scientific diversity, or executable grading feasibility.',
    ],
    'software': {'python': __import__('sys').version.split()[0], 'numpy': np.__version__, 'scipy': __import__('scipy').__version__},
}
data['selection']['initial_review_window'] = {'bioconda_package_rows': 110, 'bioconductor_package_rows': 110, 'interpretation': 'Arbitrary initial screening windows, followed by manual selection and adjacent leads; no scientific threshold or exhaustive ranking.'}
data['selection']['current_step'] = 'Hold the 95-entry cohort fixed for adoption metric comparison before selecting a 200-entry cohort and inspecting its diversity.'
resources()
(CACHE / 'inventory-enriched.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
print('coverage', data['adoption_analysis']['coverage'])
for p in pairs:
    print(p['x'], p['y'], 'n', p['n'], 'rho', p['spearman_rho'], 'log_r', p['pearson_log1p_r'], 'raw_r', p['pearson_raw_r'])
print('PyPI rows')
for r in sorted((r for r in records if r['pypi_packages']), key=lambda r:r['adoption_metrics']['pypi_max_package_downloads_30d'], reverse=True):
    print(r['name'],r['adoption_metrics'])
print('sensitivity single')
for p in data['adoption_analysis']['sensitivity_single_package_entries']:
    print(p['x'],p['y'],p['n'],p['spearman_rho'])
print('sensitivity no libraries')
for p in data['adoption_analysis']['sensitivity_excluding_scientific_libraries']:
    print(p['x'],p['y'],p['n'],p['spearman_rho'])
print('end', datetime.datetime.now(datetime.UTC).isoformat(), flush=True)
