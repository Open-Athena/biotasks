import collections
import csv
import json
from pathlib import Path

ROOT = Path('/tmp/bio-discovery-20260929/adoption')
DEST = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments')
VISUAL = Path('/home/exedev/.codex/visualizations/2026/09/29/01a0eece-d603-7e42-ae1b-92b907b8302a')
path = DEST / 'bio-repository-inventory.json'
data = json.loads(path.read_text())
rows = json.loads((ROOT / 'topics-mappings.json').read_text())
by_name = {r['name']:r for r in rows}
counts = collections.Counter(t for r in rows for t in r['topics'])
frequencies = [{'topic':t,'repository_count':n,'candidates':[r['name'] for r in rows if t in r['topics']]} for t,n in sorted(counts.items(),key=lambda x:(-x[1],x[0]))]
groups = {
    'Broad biology searches': ['bioinformatics','genomics','computational-biology','biology'],
    'Transcriptomics and single-cell data': ['rna-seq','rnaseq','scrna-seq','single-cell-rna-seq','single-cell','single-cell-genomics','transcriptomics','gene-expression','transcriptome'],
    'Microbial and community sequence analysis': ['metagenomics','microbiome','amplicon','metabarcoding','taxonomy','taxonomic-classification','taxonomic-profiling','metagenome-assembly','bacterial-genomes'],
    'Evolution and phylogenetic trees': ['phylogenetics','phylogenetic-trees','evolution','comparative-genomics'],
    'Chromatin assays': ['chip-seq','atac-seq','dnase-seq','peak-caller'],
    'Proteomics and protein structure': ['proteomics','protein-identification','protein-structure','protein-structure-alignment'],
    'Assembly and genome annotation': ['genome-assembly','genome-assembly-evaluation','genome-annotation','gene-finding','transcriptome-assembly'],
    'Functional enrichment': ['enrichment-analysis','gene-set-enrichment','pathway-enrichment-analysis','gsea'],
}
group_records = []
for name,tags in groups.items():
    assert all(t in counts for t in tags)
    members = [r['name'] for r in rows if set(tags).intersection(r['topics'])]
    group_records.append({'label':name,'observed_topics':tags,'repository_count':len(members),'candidates':members})
for record in data['candidates']:
    if record['name'] in by_name:
        row=by_name[record['name']]
        record['github_metadata']['topics'] = row['topics']
        record['github_topics_observation'] = {k:v for k,v in row.items() if k not in ('name','full_name','topics')}
        record['github_topics_status'] = 'queried; topics present' if row['topics'] else 'queried; empty topic list'
    else:
        record['github_topics_status'] = 'not queried; no verified GitHub mapping in this pass'
data['github_topic_analysis'] = {
    'observed_on':'2026-09-29', 'candidate_count':95, 'github_repositories_queried':len(rows),
    'repositories_with_topics':sum(bool(r['topics']) for r in rows),
    'repositories_without_topics':sum(not r['topics'] for r in rows),
    'candidates_without_verified_github_mapping':12,
    'distinct_topics':len(counts), 'topic_assignments':sum(counts.values()),
    'counting_rule':'Count each exact topic string at most once per repository. No stemming, alias merging or spelling correction in raw frequencies.',
    'source':{'endpoint':'https://api.github.com/graphql','query':json.loads((ROOT/'topics-query.json').read_text())['query'],'response_sha256':rows[0]['response_sha256']},
    'frequencies':frequencies,
    'search_ideas':group_records,
    'limitations':[
        'Topics were collected after selecting the cohort; no topic filter was used to select these 95 entries.',
        'Search ideas are analyst groupings of observed strings, not a biological diversity classification. Groups overlap; counts must not be summed.',
        'Thirty of 83 queried GitHub repositories have no topics. No topics does not imply no biological purpose.',
        'Topics mix biological areas, assays, algorithms, programming languages, file formats, product names and general tooling.',
        'Observed variants include rna-seq/rnaseq and the typo bioinfomatics. Raw strings are retained; any search expansion should document aliases.',
        'Public repositories on other hosts and versioned source archives remain eligible regardless of GitHub topics.',
        'A search limited to this cohort\'s observed tags inherits the cohort\'s selection bias and cannot establish full coverage of biology.',
    ],
}
data['sources'].append({'id':'github-topics','url':'https://docs.github.com/en/graphql/reference/objects#repositorytopic','observed_on':'2026-09-29','repositories':83,'metric':'Exact repository topic strings from repositoryTopics, with pagination completion checked.'})
path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')

with (VISUAL/'biology-repository-topics.csv').open('w',newline='') as handle:
    writer=csv.DictWriter(handle,fieldnames=['name','github_url','topic_count','topics','observed_on'])
    writer.writeheader()
    for r in rows:
        writer.writerow({'name':r['name'],'github_url':r['repository_url'],'topic_count':len(r['topics']),'topics':';'.join(r['topics']),'observed_on':r['observed_on']})
with (VISUAL/'biology-topic-frequencies.csv').open('w',newline='') as handle:
    writer=csv.DictWriter(handle,fieldnames=['topic','repository_count','candidates'])
    writer.writeheader()
    writer.writerows({'topic':r['topic'],'repository_count':r['repository_count'],'candidates':';'.join(r['candidates'])} for r in frequencies)

section = '''## GitHub topics observed in the existing cohort

Topics were collected after selection, without expanding the 95 candidates.
All 83 verified GitHub repositories were queried on September 29, 2026:
53 have topics, 30 have none, and their 341 assignments contain 214 distinct
topic strings. The remaining 12 candidates have no verified GitHub mapping in
this pass. The JSON contains every repository's exact tags, the full frequency
table, source query and response hash in `github_topic_analysis`.

The most frequent tags are `bioinformatics` (32 repositories), `genomics` (12),
`python` (10), `ngs` (6), and `bioconductor`, `bioconductor-package` and
`sequence-alignment` (5 each). `computational-biology` and `biology` appear
only once each. Counts describe tagging within this cohort, not the total
number of GitHub repositories carrying each topic.

These observed topic families provide search ideas. Each row's count is the
union of repositories carrying any listed tag, counted once within that row.
Rows overlap and are not a biological diversity classification.

| Search idea | Observed topic strings | Repositories in this cohort |
| --- | --- | ---: |
'''
for r in group_records:
    section += f"| {r['label']} | "+', '.join(f'`{t}`' for t in r['observed_topics'])+f" | {r['repository_count']} |\n"
section+='''
The broad biology row reaches only 33 of the 83 GitHub repositories. SAMtools,
DESeq2, STAR, BEDTools and PLINK have no topics. Topics therefore provide
additional discovery paths while package metadata and documentation remain
necessary. Absence of a topic does not establish absence of a scientific use.

Preserve aliases when planning searches: `rna-seq` and `rnaseq` are distinct
strings, and pyBigWig uses the misspelling `bioinfomatics`. Language tags such
as `python`, file formats such as `fastq`, and generic tags such as `pipeline`
need a biological qualifier or subsequent relevance review. Starting from
these observed tags also inherits the current inventory's coverage bias.

'''
report_path=DEST/'computational_biology_bioinformatics_packages.md'
report=report_path.read_text().replace('\n\n| GitHub stars, September', '\n| GitHub stars, September')
assert '## GitHub topics observed' not in report
report=report.replace('## Candidate inventory\n',section+'## Candidate inventory\n')
report_path.write_text(report)
print(json.dumps({k:v for k,v in data['github_topic_analysis'].items() if k in ['repositories_with_topics','repositories_without_topics','distinct_topics','topic_assignments']}))
print('group counts',[(r['label'],r['repository_count']) for r in group_records])
