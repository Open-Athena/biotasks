import collections
import datetime
import json
import os
from pathlib import Path

ROOT = Path('/tmp/bio-discovery-20260929')
DEST = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments')
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))) * 1024
assert mem >= 2.5*1024**3 and mem-100*1024**2 >= 2*1024**3 and os.getloadavg()[0] < 1.5
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated working set 100 MiB')
data = json.loads((ROOT/'inventory-checked.json').read_text())
records = data.pop('repositories')
data['candidates'] = records
data['scope'] = 'Initial package-led repository discovery pass for Marin issue #9257; no task authoring or execution validation.'
data['selection'] = {
    'baseline_entries': 50, 'added_software_entries': 45,
    'method': 'Retain the earlier inventory; review leading Bioconda and Bioconductor download entries and follow selected adjacent scientific uses.',
    'coverage': 'Package-led pass; workflow, tutorial and paper-analysis repository discovery remains incomplete.',
    'count_policy': 'No repository-count cutoff or composite adoption score. This is a reviewed batch, not an exhaustive ranking.',
    'support_packages': 'General Perl modules, compression libraries, package managers and generic containers were not promoted solely by download count.',
}
by_name = {record['name']: record for record in records}
by_name['MEME Suite']['notes'].append(
    'Official installation documentation describes repository access as restricted to developers; source tarballs are distributed publicly.')
by_name['MEME Suite']['documentation_urls'].append('https://meme-suite.org/meme/doc/install.html')
by_name['Entrez Direct']['notes'].append('Recipe identifies an NCBI source distribution; public repository identity remains unresolved.')
by_name['ViennaRNA']['documentation_urls'].append('https://www.tbi.univie.ac.at/RNA/tutorial/')
by_name['ViennaRNA']['example_data_status'] = 'Tutorial inspected: worked RNA structure examples; biological-data provenance not assessed.'
by_name['sourmash']['documentation_urls'].append('https://sourmash.readthedocs.io/en/latest/tutorials.html')
by_name['sourmash']['example_data_status'] = 'Tutorial index inspected; example inputs not downloaded or validated.'
by_name['dada2']['documentation_urls'].append('https://benjjneb.github.io/dada2/tutorial.html')
by_name['dada2']['example_data_status'] = (
    'Tutorial inspected: paired-end 16S mouse-gut reads linked through the mothur MiSeq SOP; '
    'inputs not downloaded, executed or checked for redistribution.')
data['additional_sources'] = [
    {'url': 'https://mafft.cbrc.jp/alignment/software/source.html', 'observation': 'Official source page links to https://gitlab.com/sysimm/mafft.'},
    {'url': 'https://www.tbi.univie.ac.at/RNA/', 'observation': 'Official homepage links to https://github.com/ViennaRNA/ViennaRNA.'},
    {'url': 'https://meme-suite.org/meme/doc/install.html', 'observation': 'Repository access is described as restricted to developers; public source tarballs are available.'},
    {'url': 'https://benjjneb.github.io/dada2/tutorial.html', 'observation': by_name['dada2']['example_data_status']},
]
json_name = 'bio-repository-inventory.json'
(DEST/json_name).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')

text = '''# Computational biology repository discovery

The September 29, 2026 package-led pass identifies **93 distinct repository links**
and **two additional software leads with unresolved public repository access**
for [issue #9257](https://github.com/marin-community/marin/issues/9257).
It retains the 50 earlier software entries and adds 45. Entries are candidates
screened through package metadata and selected documentation. No tasks were
created, packages installed, or candidate runtimes measured in this pass.

The [structured inventory](bio-repository-inventory.json) contains package-level
counts, recipe URLs and hashes, Bioconductor release metadata, documentation
links, role labels, and unresolved questions. GitHub identity and maintenance
metadata were checked for 65 repositories; 25 Bioconductor repository links come
from release 3.23 metadata; three GitLab links come from official package sources.

The [earlier inventory](https://github.com/marin-community/marin/blob/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/docs/experiments/computational_biology_bioinformatics_packages.md)
preserves its July 28 adoption evidence. Its approximate global ranking is not
carried forward. This inventory has no repository-count cutoff or composite
score, and does not establish task suitability or scientific coverage.

## Metrics and provenance

| Observation | Definition and scope |
| --- | --- |
| Bioconda, September 29, 2026 | Cumulative recorded downloads from the [official package summary](https://github.com/bioconda/bioconda-stats/blob/cd491b0a4c9a7e80069c8894fbd369d8b07ceddc/package-downloads/anaconda.org/bioconda/packages.tsv), containing 12,740 packages. The [collector](https://github.com/bioconda/bioconda-stats/blob/main/src/package_downloads/stats_from_anaconda_org.py) sums nonnegative file counters across versions, builds and platforms for main-label conda artifacts. |
| Bioconductor, data as of September 28, 2026 | [Download score](https://www.bioconductor.org/packages/stats/): average monthly distinct IPs over September 2025 through August 2026. The retrieved score table contains 3,118 package entries. This is not a count of distinct users across the whole year. |
| Package-to-source mapping | [Bioconda recipe revision](https://github.com/bioconda/bioconda-recipes/tree/254ba2d4bcda7fe6ed2baa586bac6c35885a4b10/recipes), individually pinned conda-forge recipes, and [Bioconductor 3.23 metadata](https://bioconductor.org/packages/3.23/bioc/VIEWS). The JSON preserves selected fields and source hashes. |

A recent-window Bioconda download total has not been computed. The cumulative
counter is useful for initial discovery, but it favors older packages and
includes dependency installations and automation. Channel migrations, mirrors,
containers and other installation methods also affect interpretation. Do not
combine it with the Bioconductor score or infer researcher counts from either.

Packages sharing a repository retain separate counters. PLINK/PLINK 2,
MACS2/MACS3, Snakemake variants and the sampled UCSC utilities each occupy one
entry. Libraries such as HTSlib and GenomicRanges remain useful candidates, with
dependency-driven adoption called out. General Perl and compression dependencies
were not selected solely because they have high counts.

## Source identity and inspection findings

- MAFFT's [official source page](https://mafft.cbrc.jp/alignment/software/source.html)
  points to `gitlab.com/sysimm/mafft`; the earlier inventory linked a GitHub mirror.
- The current `iqtree` recipe points to IQ-TREE 3. The earlier IQ-TREE 2 URL is
  retained as historical provenance in the JSON.
- MAFFT, Biopython and Scanpy have current conda-forge recipes. Their Bioconda
  counters cover only the Bioconda distribution history.
- The current Bioconductor release describes scuttle as legacy utilities.
  Review its present role and alternatives before selecting scientific examples.
- HTSeq is marked as a fork by GitHub. Its package recipe identifies
  `htseq/htseq`; resolve that relationship during deeper inspection.
- MEME's [installation documentation](https://meme-suite.org/meme/doc/install.html)
  describes developer-only repository access and public source tarballs. Entrez
  Direct's recipe identifies an NCBI distribution, but this pass did not resolve
  a public repository. Both are retained below as source leads.
- DADA2's [tutorial](https://benjjneb.github.io/dada2/tutorial.html) links observed
  paired-end 16S mouse-gut reads and connects sequence processing to community
  analysis with phyloseq. ViennaRNA has worked structure examples, and sourmash
  has a tutorial index. Inputs were not downloaded or checked for redistribution.

## Candidate inventory

Rows are alphabetical within role. `B` is the Bioconda cumulative counter and
`C` is the separate Bioconductor score. An em dash means no observation was
collected for that metric. For entries with multiple packages, the JSON contains
each counter; no repository-level total is presented. Documentation links are
inspection starting points. Example data remain uninspected except where noted
in the JSON.

'''
roles = ['scientific tool', 'scientific library', 'visualization tool', 'retrieval tool', 'workflow infrastructure']
for role in roles:
    text += f'### {role.capitalize()}s\n\n'
    text += '| Repository | Scientific use | B | C | Documentation | Added this pass |\n| --- | --- | ---: | ---: | --- | --- |\n'
    for record in sorted((r for r in records if r['role']==role and r['repository_url']), key=lambda r:r['name'].lower()):
        packages = record['bioconda_packages']
        count = f"{packages[0]['cumulative_downloads']:,}" if len(packages)==1 else (f'{len(packages)} package counters' if packages else '—')
        score = f"{record['bioconductor_download_score']:,}" if record['bioconductor_download_score'] is not None else '—'
        doc_url = record['documentation_urls'][0] if record['documentation_urls'] else record['repository_url']
        added = 'yes' if record['previous_inventory_rank'] is None else ''
        text += f"| [{record['name']}]({record['repository_url']}) | {record['scientific_use']} | {count} | {score} | [docs]({doc_url}) | {added} |\n"
    text += '\n'
text += '''## Unresolved source leads

| Software | Scientific use | Bioconda cumulative downloads | Source route |
| --- | --- | ---: | --- |
'''
for record in records:
    if record['repository_url']:
        continue
    text += f"| {record['name']} | {record['scientific_use']} | {record['bioconda_packages'][0]['cumulative_downloads']:,} | [documentation]({record['documentation_urls'][0]}) |\n"
text += '''
`harpy`, `genenotebook` and `genoboo` also appeared among highly downloaded
packages. Their counters are recorded in the JSON, but their scientific purpose
and independent use have not been inspected. Their download counts alone do not
establish priority.

## Remaining discovery coverage

This pass is concentrated on packaged tools and scientific libraries. Follow
their tutorials, dependency manifests and citations into reusable workflows and
paper-analysis repositories. The
[Snakemake workflow catalog](https://snakemake.github.io/snakemake-workflow-catalog/),
[nf-core pipelines](https://nf-co.re/pipelines),
[Galaxy training material](https://training.galaxyproject.org/) and
[Bioconductor workflows](https://bioconductor.org/packages/release/workflows/)
provide complementary discovery routes. A low-download paper repository may
still provide an observed dataset and a well-defined scientific question.

Continue recording source identity, scientific use, adoption evidence,
documentation, data leads and uncertainties. Source discovery can proceed while
a separate prototype investigates task extraction from one known repository;
candidate status does not depend on that prototype succeeding.
'''
(DEST/'computational_biology_bioinformatics_packages.md').write_text(text)
print('end', datetime.datetime.now(datetime.UTC).isoformat())
print('candidate roles', dict(collections.Counter(r['role'] for r in records)))
print('markdown bytes', len(text.encode()), 'json bytes', (DEST/json_name).stat().st_size)
