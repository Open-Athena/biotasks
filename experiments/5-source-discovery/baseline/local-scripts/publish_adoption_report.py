import csv
import datetime
import hashlib
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path('/tmp/bio-discovery-20260929')
DEST = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments')
VISUAL = Path('/home/exedev/.codex/visualizations/2026/09/29/01a0eece-d603-7e42-ae1b-92b907b8302a')

mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
assert mem >= 2.5*1024**3 and mem - 250*1024**2 >= 2*1024**3 and os.getloadavg()[0] < 1.5
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated peak 250 MiB', flush=True)
data = json.loads((ROOT / 'adoption/inventory-enriched.json').read_text())
records = data['candidates']
analysis = data['adoption_analysis']
data['sources'].extend([
    {'id': 'pypistats', 'url': 'https://pypistats.org/api/', 'observed_on': '2026-09-29', 'metric': 'Downloads excluding known mirrors, summed over August 30 through September 28, 2026; daily observations and per-package API URLs retained.', 'matched_candidates': 19, 'matched_packages': 20},
    {'id': 'pypi-metadata', 'url': 'https://docs.pypi.org/api/json/', 'observed_on': '2026-09-29', 'purpose': 'Verify package identity through project URLs and official installation documentation.'},
    {'id': 'github-stars', 'url': 'https://docs.github.com/en/rest/repos/repos#get-a-repository', 'observed_on': '2026-09-29', 'metric': 'stargazers_count from each verified repository; original 65 repositories plus 18 linked by Bioconductor release URL or BugReports.', 'matched_candidates': 83},
])
data['metric_limitations'].extend([
    'GitHub stars measure repository interest; they are not installations or a measure of scientific suitability.',
    'PyPI download counts include automated and dependency downloads, are affected by caches, and omit other distribution channels.',
    'Adoption correlations are descriptive of this selected 95-entry cohort; the pairs have different overlap populations and time windows.',
])
data['additional_sources'].extend([
    {'url': 'https://packaging.python.org/en/latest/guides/analyzing-pypi-package-downloads/', 'observation': 'PyPA explains caching, mirrors, automated downloads and data quality limitations.'},
    {'url': 'https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories#search-by-topic', 'observation': 'The topic qualifier provides a complementary repository discovery route; no topic-driven candidates were added to this fixed-cohort comparison.'},
])

labels = {
    'bioconda_max_package_downloads': 'Bioconda cumulative downloads',
    'bioconductor_download_score': 'Bioconductor score',
    'github_stars': 'GitHub stars',
    'pypi_max_package_downloads_30d': 'PyPI 30-day downloads',
}
pair_order = [(0,2),(1,2),(2,3),(0,1),(0,3),(1,3)]
keys = list(labels)
ordered = [next(p for p in analysis['pairs'] if p['x']==keys[i] and p['y']==keys[j]) for i,j in pair_order]

report_path = DEST / 'computational_biology_bioinformatics_packages.md'
old_report = report_path.read_text()
report_hash = hashlib.sha256(old_report.encode()).hexdigest()
before, after = old_report.split('## Candidate inventory\n', 1)
_, remainder = after.split('## Adoption leads to inspect\n', 1)
before = before.replace(
    'links, role labels, and unresolved questions. GitHub identity and maintenance\nmetadata were checked for 65 repositories; 25 Bioconductor repository links come\nfrom release 3.23 metadata; three GitLab links come from official package sources.',
    'links, role labels, and unresolved questions. GitHub metadata and stars are\n+verified for 83 entries, including 18 GitHub repositories linked by Bioconductor\n+release metadata. The inventory retains 25 Bioconductor source links, three\n+GitLab links, and the two source archives. PyPI downloads are verified for\n+19 entries (20 packages).'.replace('\n+', '\n'))
before = before.replace(
    'carried forward. This inventory has no repository-count cutoff or composite\nscore, and does not establish task suitability or scientific coverage.',
    'carried forward. The initial screen displayed the top 110 package rows from\n+each download table, then manually selected additions and adjacent tools.\n+The 95 entries form a reviewed batch, not a strict top-95 ranking or a scientific\n+coverage threshold. There is no composite adoption score. This comparison holds\n+the cohort fixed before choosing how to expand it to 200 and inspect diversity.'.replace('\n+', '\n'))
before = before.replace('## Metrics and provenance\n', '''The adoption comparison below finds little rank agreement between GitHub stars
and Bioconda downloads in this cohort (Spearman ρ = 0.10, n = 82). Bioconda and
Bioconductor agree more (ρ = 0.45, n = 25). PyPI overlaps only 19 candidates;
correlations cannot support a single interchangeable popularity measure.

## Metrics and provenance
'''.replace('\n+', '\n'))
metric_rows = '''| GitHub stars, September 29, 2026 | Current `stargazers_count` from each identified [repository API](https://docs.github.com/en/rest/repos/repos#get-a-repository). Bioconductor mappings use package `URL` or `BugReports` links. No arbitrary GitHub mirrors were substituted for other source hosts. |
| PyPI, August 30–September 28, 2026 | Thirty complete calendar days of downloads from [PyPIStats](https://pypistats.org/api/), excluding known mirrors. Package identity, daily counts, API URLs and response hashes are retained in the JSON. A July 1–September 28 window supports the 90-day sensitivity check. |
'''.replace('\n+', '\n')
before = before.replace('\nA recent-window Bioconda', '\n'+metric_rows+'\nA recent-window Bioconda')
before = before.replace(
    'entry. Libraries such as HTSlib and GenomicRanges remain useful candidates, with',
    'entry. For correlation only, use the largest recorded package counter per\n+entry within each registry; it is a proxy, not a repository download total.\n+Results excluding entries with multiple package counters are reported below.\n+Libraries such as HTSlib and GenomicRanges remain useful candidates, with'.replace('\n+', '\n'))

section = '''## Adoption correlation on the fixed 95-entry cohort

Coverage is 94 entries for Bioconda, 25 for Bioconductor, 83 for GitHub stars,
and 19 for PyPI. Missing measurements are excluded separately for each pair,
never converted to zero. GitHub metrics remain missing for the three GitLab
projects, the two source archives, and seven Bioconductor entries without a
verified GitHub mapping in this pass. This does not exclude those software
sources from discovery.

Spearman ρ measures agreement between rankings: +1 means identical order,
0 means no monotonic association, and −1 means reversed order. Average ranks
handle ties. Pearson correlations on raw counts and `log10(1 + count)` show
sensitivity to scale and large observations. Each row uses a different overlap
population; the correlations should not be compared as competing estimators
on the same sample.

| Measures | Matched entries | Spearman ρ | Pearson, log scale | Pearson, raw scale |
| --- | ---: | ---: | ---: | ---: |
'''.replace('\n+', '\n')
fmt = lambda v: '—' if v is None else f'{v:.2f}'
for p in ordered:
    section += f"| {labels[p['x']]} / {labels[p['y']]} | {p['n']} | {fmt(p['spearman_rho'])} | {fmt(p['pearson_log1p_r'])} | {fmt(p['pearson_raw_r'])} |\n"
section += '''
Bioconductor and PyPI have no matched candidates here, so their correlation
cannot be estimated. No inference of independence follows from that absence.

The raw stars/PyPI Pearson correlation of 0.83 is dominated by a large
observation: removing Biopython lowers it to 0.36 (n = 18). Rank correlation
is 0.29 with Biopython and 0.17 without it. Biopython records 3,815,234 PyPI
downloads in the 30-day window and 5,215 stars; pysam records 1,014,605 downloads
and 911 stars. These are channel counts and repository interest, not user counts.

Two further checks leave the broad ranking result similar:

- Excluding all entries with multiple package counters gives stars/Bioconda
  ρ = 0.07 (n = 78), Bioconda/PyPI ρ = 0.28 (n = 17), and stars/PyPI
  ρ = 0.28 (n = 17). Using sums instead of maximum package counters gives
  0.08, 0.34 and 0.31, respectively.
- Using 90 days of PyPI counts gives Bioconda/PyPI ρ = 0.36 and stars/PyPI
  ρ = 0.34 (both n = 19), versus 0.35 and 0.29 for 30 days.

Role composition matters. Excluding entries labeled scientific libraries changes
stars/PyPI ρ to 0.54 (n = 11) and stars/Bioconductor ρ to 0.27 (n = 12).
Those smaller subsets are descriptive checks, not evidence that one metric is
a universal substitute for another. Exact coefficients, pair membership and
all sensitivity results are in the JSON's `adoption_analysis` object.

The cohort was selected partly through download screens, which limits the range
and representativeness of this analysis. The time windows also differ: cumulative
Bioconda downloads, a twelve-month Bioconductor IP average, recent PyPI downloads,
and present GitHub stars. [PyPA](https://packaging.python.org/en/latest/guides/analyzing-pypi-package-downloads/)
documents additional effects from caching, mirrors and automation. Neither the
correlations nor the counts measure scientific diversity or task quality.

Keep the signals separate when defining the next discovery sample. GitHub
[topic searches](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories#search-by-topic),
such as `topic:bioinformatics` sorted by stars, can find software outside package
registries. Topics are optional and maintainer-assigned, so they are an additional
discovery route, not a complete biological classification. No new candidates
were added for this comparison.

PyPI identity checks excluded the package named `sepp`: its metadata describes
an unrelated ESA platform. BUSCO and SPAdes returned 404 under their expected
PyPI names. Other entries without a verified PyPI mapping remain missing;
alternate names and third-party wrappers have not been exhaustively searched.

## Candidate inventory

Rows are alphabetical within role. `B` is the Bioconda cumulative counter,
`C` is the Bioconductor score, and `P30` is the PyPI download count over
August 30–September 28, 2026. An em dash means no verified measurement.
Multiple packages retain individual counters in the JSON; `max*` marks the
largest recorded package counter used for correlation. Stars link to the
measured GitHub repository, which can differ from the primary source link.
Documentation links are inspection starting points; example data remain
uninspected except where noted in the JSON.

'''.replace('\n+', '\n')
role_titles = {'scientific tool':'Scientific tools', 'scientific library':'Scientific libraries', 'visualization tool':'Visualization tools', 'retrieval tool':'Retrieval tools', 'workflow infrastructure':'Workflow infrastructure'}
for role, title in role_titles.items():
    section += f'### {title}\n\n'
    section += '| Repository or source archive | Scientific use | B | C | Stars | P30 | Documentation |\n| --- | --- | ---: | ---: | ---: | ---: | --- |\n'
    for r in sorted((r for r in records if r['role']==role), key=lambda r:r['name'].lower()):
        source = r['repository_url'] or r['source_distribution']['url']
        metrics = r['adoption_metrics']
        b = '—' if metrics['bioconda_max_package_downloads'] is None else f"{metrics['bioconda_max_package_downloads']:,}"
        if len(r['bioconda_packages'])>1:
            b += ' max*'
        c = '—' if metrics['bioconductor_download_score'] is None else f"{metrics['bioconductor_download_score']:,}"
        g = '—' if metrics['github_stars'] is None else f"[{metrics['github_stars']:,}](https://github.com/{r['github_metadata']['full_name']})"
        p = '—' if metrics['pypi_max_package_downloads_30d'] is None else f"{metrics['pypi_max_package_downloads_30d']:,}"
        if len(r['pypi_packages'])>1:
            p += ' max*'
        docs = r['documentation_urls'][0] if r['documentation_urls'] else source
        section += f"| [{r['name']}]({source}) | {r['scientific_use']} | {b} | {c} | {g} | {p} | [docs]({docs}) |\n"
    section += '\n'
new_report = before + section + '## Adoption leads to inspect\n' + remainder
assert hashlib.sha256(report_path.read_bytes()).hexdigest() == report_hash, 'Report changed concurrently'
report_path.write_text(new_report)
(DEST / 'bio-repository-inventory.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')

VISUAL.mkdir(exist_ok=True, parents=True)
with (VISUAL / 'biology-adoption-95.csv').open('w', newline='') as handle:
    fields = ['name', 'repository_url', 'github_url', *keys, 'pypi_packages', 'pypi_window_start', 'pypi_window_end']
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for r in records:
        writer.writerow({'name':r['name'], 'repository_url':r['repository_url'] or r['source_distribution']['url'], 'github_url': 'https://github.com/'+r['github_metadata']['full_name'] if r.get('github_metadata') else None, **{k:r['adoption_metrics'][k] for k in keys}, 'pypi_packages':';'.join(p['name'] for p in r['pypi_packages']), 'pypi_window_start':'2026-08-30' if r['pypi_packages'] else None,'pypi_window_end':'2026-09-28' if r['pypi_packages'] else None})

colors = {'PyPI matched':'#2563eb', 'Bioconductor matched':'#15803d', 'Other entries':'#9a6d38'}
plt.rcParams.update({'font.size':9, 'axes.spines.top':False, 'axes.spines.right':False, 'svg.fonttype':'none'})
fig, axes = plt.subplots(2,3,figsize=(13.5,8.3))
short = {'bioconda_max_package_downloads':'Bioconda downloads (cumulative)', 'bioconductor_download_score':'Bioconductor score', 'github_stars':'GitHub stars', 'pypi_max_package_downloads_30d':'PyPI downloads (30 days)'}
for ax, pair in zip(axes.flat, ordered):
    if pair['n']==0:
        ax.axis('off')
        ax.text(0.06,0.88,'Coverage of the 95 candidates',fontsize=12,fontweight='bold',va='top')
        ax.text(0.06,0.76,'Bioconda     94\nGitHub stars 83\nBioconductor 25\nPyPI         19',fontfamily='monospace',fontsize=11,linespacing=1.8,va='top')
        ax.text(0.06,0.37,'Bioconductor × PyPI: no matched entries.\n\nSelected cohort; not all biology software.\nMissing values excluded separately per pair.\nMaximum package counter per entry.\nPyPI: Aug 30–Sep 28, 2026; mirrors excluded.',fontsize=9,linespacing=1.6,va='top')
        continue
    rs=[r for r in records if r['name'] in pair['members']]
    for group,color in colors.items():
        subset=[r for r in rs if ('PyPI matched' if r['pypi_packages'] else ('Bioconductor matched' if r['bioconductor_package'] else 'Other entries'))==group]
        ax.scatter([r['adoption_metrics'][pair['x']] for r in subset],[r['adoption_metrics'][pair['y']] for r in subset],s=29,c=color,alpha=.75,edgecolors='white',linewidths=.3)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(short[pair['x']]); ax.set_ylabel(short[pair['y']])
    ax.set_title(f"Spearman ρ = {pair['spearman_rho']:.2f}   |   n = {pair['n']}",loc='left',fontweight='bold')
    ax.grid(which='major',alpha=.15)
    for r in rs:
        if r['name'] in ['Biopython','pysam'] and pair['y']=='pypi_max_package_downloads_30d':
            ax.annotate(r['name'],(r['adoption_metrics'][pair['x']],r['adoption_metrics'][pair['y']]),xytext=(-5,-12),textcoords='offset points',ha='right',fontsize=8)
fig.suptitle('Adoption signals rank these biology tools differently',x=.055,ha='left',fontsize=17,fontweight='bold')
fig.text(.055,.927,'95 fixed candidates • observed September 29, 2026 • logarithmic axes',fontsize=11,color='#444444')
fig.legend(handles=[Line2D([0],[0],marker='o',linestyle='',markerfacecolor=c,markeredgecolor='none',label=g) for g,c in colors.items()],loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.008))
fig.tight_layout(rect=(0,.045,1,.9),h_pad=2.7,w_pad=2.5)
fig.savefig(VISUAL/'biology-adoption-correlations.png',dpi=170)
fig.savefig(VISUAL/'biology-adoption-correlations.svg')
plt.close(fig)
mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
assert mem >= 2*1024**3 and os.getloadavg()[0] <= 2.5
print('end', datetime.datetime.now(datetime.UTC).isoformat(), 'report, JSON, CSV, PNG and SVG written',flush=True)
