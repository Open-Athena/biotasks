import collections
import csv
import datetime
import json
import math
import os
from pathlib import Path
import statistics
import subprocess

ROOT = Path('/tmp/bio-discovery-20260929')
DEST = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments/bio-task-generation/01-discovery')


def ranks(values):
    positions = collections.defaultdict(list)
    for i, value in enumerate(sorted(values), 1):
        positions[value].append(i)
    return [statistics.mean(positions[value]) for value in values]


def verify_pair(rows, expected):
    x_key, y_key = expected['x'], expected['y']
    matched = [r for r in rows if r['adoption_metrics'][x_key] is not None and r['adoption_metrics'][y_key] is not None]
    assert expected['n']==len(matched)
    assert expected['members']==[r['name'] for r in matched]
    if len(matched)<3:
        assert expected['spearman_rho'] is None
        return
    x=[r['adoption_metrics'][x_key] for r in matched]
    y=[r['adoption_metrics'][y_key] for r in matched]
    results = {
        'spearman_rho':statistics.correlation(ranks(x),ranks(y)),
        'pearson_raw_r':statistics.correlation(x,y),
        'pearson_log1p_r':statistics.correlation([math.log10(1+v) for v in x],[math.log10(1+v) for v in y]),
    }
    for k,value in results.items():
        assert math.isclose(value,expected[k],abs_tol=1e-12), (k,value,expected[k])


mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert mem>=2.5*1024**3 and mem-150*1024**2>=2*1024**3 and os.getloadavg()[0]<1.5
print('start',datetime.datetime.now(datetime.UTC).isoformat(),'estimated peak 150 MiB',flush=True)
d=json.loads((DEST/'inventory.json').read_text())
rows=d['candidates']
assert len(rows)==len({r['name'] for r in rows})==95
baseline=json.loads((ROOT/'inventory-checked.json').read_text())['repositories']
assert [r['name'] for r in rows]==[r['name'] for r in baseline]
assert all(r['execution_status']=='not run' for r in rows)
by_name={r['name']:r for r in rows}
for name in ['MEME Suite','Entrez Direct']:
    assert by_name[name]['discovery_priority']=='high'
    assert by_name[name]['source_distribution']['availability_check']['http_status']==200
bioconda={r['package']:int(r['total']) for r in csv.DictReader((ROOT/'bioconda-packages.tsv').open(),delimiter='\t')}
bioc={r['Package']:int(r['Download_score']) for r in csv.DictReader((ROOT/'bioconductor-scores.tsv').open(),delimiter='\t')}
for row in rows:
    for p in row['bioconda_packages']:
        assert p['cumulative_downloads']==bioconda[p['name']]
    if row['bioconductor_package']:
        assert row['bioconductor_download_score']==bioc[row['bioconductor_package']]
    for p in row['pypi_packages']:
        assert len(p['daily_downloads'])==90
        recent={date:value for date,value in p['daily_downloads'].items() if date>=p['window_start']}
        assert len(recent)==30
        assert p['downloads_30d']==sum(recent.values())
        assert p['downloads_90d']==sum(p['daily_downloads'].values())
        assert list(p['daily_downloads'])==[(datetime.date(2026,7,1)+datetime.timedelta(days=i)).isoformat() for i in range(90)]
        assert p['window_start']=='2026-08-30' and p['window_end']=='2026-09-28'
for group in ['pairs','sensitivity_summed_package_counters','sensitivity_pypi_90d']:
    for p in d['adoption_analysis'][group]:
        verify_pair(rows,p)
for p in d['adoption_analysis']['sensitivity_single_package_entries']:
    verify_pair([r for r in rows if len(r['bioconda_packages'])<=1 and len(r['pypi_packages'])<=1],p)
for p in d['adoption_analysis']['sensitivity_excluding_scientific_libraries']:
    verify_pair([r for r in rows if r['role']!='scientific library'],p)
gh_rows=[r for r in rows if r.get('github_metadata')]
topic_rows=json.loads((ROOT/'adoption/topics-mappings.json').read_text())
assert len(gh_rows)==len(topic_rows)==83
assert len({r['github_metadata']['full_name'].lower() for r in gh_rows})==83
for r in topic_rows:
    record=by_name[r['name']]
    assert r['full_name'].lower()==record['github_metadata']['full_name'].lower()
    assert r['topics']==record['github_metadata']['topics']
counts=collections.Counter(t for r in gh_rows for t in r['github_metadata']['topics'])
assert len(counts)==214 and sum(counts.values())==341
assert sum(not r['github_metadata']['topics'] for r in gh_rows)==30
assert {r['topic']:r['repository_count'] for r in d['github_topic_analysis']['frequencies']}==dict(counts)
for t in d['github_topic_analysis']['frequencies']:
    assert t['repository_count']==len(t['candidates'])
report=(DEST/'index.md').read_text()
inventory=report.split('## Candidate inventory\n')[1].split('## Adoption leads to inspect\n')[0]
assert len([x for x in inventory.splitlines() if x.startswith('| [')])==95
assert all(f'[{r["name"]}](' in inventory for r in rows)
assert '|\n\n| GitHub stars' not in report
print('verified: unchanged 95 candidates; metric joins; daily windows; independently recomputed correlations; all 83 topic lists; 95 rendered rows',flush=True)
files = sorted(p for p in DEST.rglob('*') if p.is_file())
args = ['./infra/pre-commit.py']
for path in files:
    args.extend(['--files', str(path)])
proc=subprocess.run(args)
print('end',datetime.datetime.now(datetime.UTC).isoformat(),'lint exit',proc.returncode,flush=True)
raise SystemExit(proc.returncode)
