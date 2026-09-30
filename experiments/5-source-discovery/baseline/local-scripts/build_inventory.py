import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path('/tmp/bio-discovery-20260929')
DEST = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments')
BIOCONDA_REVISION = '254ba2d4bcda7fe6ed2baa586bac6c35885a4b10'
STATS_REVISION = 'cd491b0a4c9a7e80069c8894fbd369d8b07ceddc'
PRIOR_URL = 'https://github.com/marin-community/marin/blob/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/docs/experiments/computational_biology_bioinformatics_packages.md'

with (ROOT/'bioconda-packages.tsv').open() as handle:
    conda_counts = {row['package']: int(row['total']) for row in csv.DictReader(handle, delimiter='\t')}
with (ROOT/'bioconductor-scores.tsv').open() as handle:
    bioc_scores = {row['Package']: int(row['Download_score']) for row in csv.DictReader(handle, delimiter='\t')}
bioc_metadata = json.loads((ROOT/'bioconductor-metadata.json').read_text())
forge_recipes = {row['package']: row for row in json.loads((ROOT/'conda-forge-recipes.json').read_text())}

old_packages = {
    1: ['blast'], 2: ['samtools'], 3: ['bwa'], 4: ['bowtie2'], 5: ['bioconductor-deseq2'],
    6: ['star'], 7: ['bedtools'], 8: ['gatk4'], 9: ['pysam'], 10: ['mafft'],
    11: ['hmmer'], 12: [], 13: ['minimap2'], 14: ['bcftools'], 15: ['picard'],
    16: ['snakemake', 'snakemake-minimal'], 17: ['htslib'], 18: ['fastqc'], 19: ['biopython'],
    20: ['nextflow'], 21: ['diamond'], 22: ['plink', 'plink2'], 23: ['scanpy'], 24: ['multiqc'],
    25: ['bioconductor-edger'], 26: ['bioconductor-limma'], 27: ['spades'], 28: ['iqtree'],
    29: ['fasttree'], 30: ['raxml'], 31: ['cutadapt'], 32: ['salmon'], 33: ['kallisto'],
    34: ['stringtie'], 35: ['fastp'], 36: ['sra-tools'], 37: ['deeptools'], 38: ['vcftools'],
    39: ['snpeff'], 40: ['ensembl-vep'], 41: ['macs2', 'macs3'], 42: ['mmseqs2'],
    43: ['muscle'], 44: ['kraken2'], 45: ['busco'],
    46: ['ucsc-liftover', 'ucsc-bedgraphtobigwig', 'ucsc-bigwigtobedgraph', 'ucsc-fatotwobit',
         'ucsc-twobittofa', 'ucsc-bedtobigbed', 'ucsc-bigbedtobed'],
    47: ['bioconductor-genomicranges'], 48: ['bioconductor-biostrings'], 49: ['pybedtools'],
    50: ['nf-core'],
}
old_bioc = {5: 'DESeq2', 25: 'edgeR', 26: 'limma', 47: 'GenomicRanges', 48: 'Biostrings'}
extra_conda = [
    ('LAST', 'last', 'Sequence alignment', 'scientific tool'),
    ('MEME Suite', 'meme', 'Sequence motif discovery and scanning', 'scientific tool'),
    ('BBTools', 'bbmap', 'Read alignment, filtering and sequence processing', 'scientific tool'),
    ('Entrez Direct', 'entrez-direct', 'NCBI database retrieval and record transformation', 'retrieval tool'),
    ('ViennaRNA', 'viennarna', 'RNA secondary structure prediction', 'scientific tool'),
    ('HyPhy', 'hyphy', 'Comparative sequence analysis and molecular evolution', 'scientific tool'),
    ('SEPP', 'sepp', 'Phylogenetic placement', 'scientific tool'),
    ('HTSeq', 'htseq', 'Read counting and sequencing-data processing', 'scientific library'),
    ('VSEARCH', 'vsearch', 'Sequence clustering and metagenomic sequence analysis', 'scientific tool'),
    ('FreeBayes', 'freebayes', 'Haplotype-based variant calling', 'scientific tool'),
    ('SeqKit', 'seqkit', 'FASTA and FASTQ processing', 'scientific tool'),
    ('seqtk', 'seqtk', 'FASTA and FASTQ processing', 'scientific tool'),
    ('SearchGUI', 'searchgui', 'Proteomics identification search engines', 'scientific tool'),
    ('PeptideShaker', 'peptide-shaker', 'Proteomics identification interpretation', 'scientific tool'),
    ('Prokka', 'prokka', 'Prokaryotic genome annotation', 'scientific tool'),
    ('QUAST', 'quast', 'Genome assembly quality assessment', 'scientific tool'),
    ('CheckM', 'checkm-genome', 'Microbial genome quality assessment', 'scientific tool'),
    ('Mash', 'mash', 'Sequence distance estimation with sketches', 'scientific tool'),
    ('sourmash', 'sourmash', 'Genome and metagenome comparison with sketches', 'scientific tool'),
    ('BEDOPS', 'bedops', 'Genomic interval operations', 'scientific tool'),
    ('BamTools', 'bamtools', 'BAM manipulation', 'scientific library'),
    ('pyBigWig', 'pybigwig', 'bigWig signal access', 'scientific library'),
    ('pyfaidx', 'pyfaidx', 'Indexed FASTA access', 'scientific library'),
    ('cyvcf2', 'cyvcf2', 'VCF parsing', 'scientific library'),
    ('DendroPy', 'dendropy', 'Phylogenetic trees and comparative data', 'scientific library'),
]
extra_bioc = [
    ('fgsea', 'Gene-set enrichment', 'scientific tool'),
    ('clusterProfiler', 'Functional enrichment of omics results', 'scientific tool'),
    ('GSVA', 'Gene-set variation analysis', 'scientific tool'),
    ('ggtree', 'Phylogenetic tree annotation and visualization', 'visualization tool'),
    ('treeio', 'Phylogenetic tree formats and metadata', 'scientific library'),
    ('ComplexHeatmap', 'Annotated heatmaps for molecular measurements', 'visualization tool'),
    ('scater', 'Single-cell quality control and exploratory analysis', 'scientific tool'),
    ('scuttle', 'Legacy single-cell analysis utilities', 'scientific library'),
    ('scran', 'Single-cell normalization and statistical analysis', 'scientific tool'),
    ('phyloseq', 'Microbiome community analysis', 'scientific tool'),
    ('dada2', 'Amplicon sequence inference', 'scientific tool'),
    ('SingleR', 'Reference-based cell-type annotation', 'scientific tool'),
    ('sva', 'Surrogate variables and batch effects', 'scientific tool'),
    ('tximport', 'Transcript-to-gene quantification import', 'scientific library'),
    ('GEOquery', 'GEO study retrieval', 'retrieval tool'),
    ('biomaRt', 'BioMart annotation retrieval', 'retrieval tool'),
    ('rtracklayer', 'Genome annotation file import and export', 'scientific library'),
    ('GenomicFeatures', 'Gene models and transcript annotations', 'scientific library'),
    ('VariantAnnotation', 'Variant annotation and VCF processing', 'scientific library'),
    ('ShortRead', 'FASTQ processing and quality assessment', 'scientific library'),
]


def recipe(package):
    package = 'snakemake' if package == 'snakemake-minimal' else package
    path = ROOT/'recipes'/f'{package}.yaml'
    if not path.exists():
        return None
    content = path.read_text()
    variables = dict(re.findall(r'{% set (\w+) = ["\']([^"\']+)["\'] %}', content))
    def expand(text):
        for key, value in variables.items():
            text = text.replace('{{ '+key+' }}', value)
        return text
    fields = {key: expand(value.strip('"\'')) for key, value in
              re.findall(r'^  (home|dev_url|doc_url|summary|license):\s*(.+)$', content, re.M)}
    url = forge_recipes[package]['url'] if package in forge_recipes else (
        f'https://raw.githubusercontent.com/bioconda/bioconda-recipes/{BIOCONDA_REVISION}/recipes/{package}/meta.yaml')
    fields.update(source_url=url, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  package_version=variables.get('version'))
    return fields


def candidate(name, repository, purpose, role, packages, bioc=None, previous=None):
    recipes = [value for package in packages if (value := recipe(package)) is not None]
    record = {
        'name': name, 'repository_url': repository, 'scientific_use': purpose, 'role': role,
        'discovery_route': 'previous inventory' if previous else 'package download screen',
        'previous_inventory_rank': previous, 'inspection_status': 'metadata screened',
        'bioconda_packages': [{'name': package, 'cumulative_downloads': conda_counts.get(package)} for package in packages],
        'bioconductor_package': bioc,
        'bioconductor_download_score': bioc_scores.get(bioc) if bioc else None,
        'source_records': recipes,
        'documentation_urls': list(dict.fromkeys(r.get('doc_url', r.get('home', '')) for r in recipes)),
        'example_data_status': 'not inspected', 'execution_status': 'not run',
        'source_access': 'repository link identified', 'notes': [],
    }
    if bioc:
        metadata = bioc_metadata[bioc]
        record['bioconductor_metadata'] = {key: metadata.get(key) for key in (
            'Version', 'Title', 'License', 'URL', 'git_url', 'git_branch', 'git_last_commit',
            'git_last_commit_date', 'vignettes', 'Suggests')}
        record['repository_url'] = metadata['git_url']
        record['documentation_urls'] = [
            'https://bioconductor.org/packages/3.23/bioc/'+v.strip()
            for v in metadata.get('vignettes', '').split(',') if v.strip()]
    return record


records = []
for line in Path('/tmp/bio-discovery-prior-inventory.md').read_text().splitlines():
    if not re.match(r'\| \d+ \|', line):
        continue
    cells = [cell.strip() for cell in line.strip('|').split('|')]
    rank = int(cells[0])
    name, repository = re.fullmatch(r'\[(.+)\]\((.+)\)', cells[1]).groups()
    role = 'workflow infrastructure' if rank in {16, 20, 50} else 'scientific tool'
    if rank in {9, 17, 19, 47, 48, 49}:
        role = 'scientific library'
    if rank == 36:
        role = 'retrieval tool'
    record = candidate(name, repository, cells[3], role, old_packages[rank], old_bioc.get(rank), rank)
    record['previous_repository_url'] = repository
    if rank == 10:
        record['repository_url'] = 'https://gitlab.com/sysimm/mafft'
        record['notes'].append('Official source link replaces the earlier GSLBiotech mirror.')
    if rank == 28:
        record['repository_url'] = 'https://github.com/iqtree/iqtree3'
        record['notes'].append('Current iqtree recipe targets IQ-TREE 3; prior inventory linked IQ-TREE 2.')
    if rank in {10, 19, 23}:
        record['notes'].append('Current recipe inspected on conda-forge; Bioconda counter covers that channel only.')
    if rank == 12:
        record['documentation_urls'] = ['https://satijalab.org/seurat/']
        record['notes'].append('Retained from earlier inventory; no current comparable download observation collected.')
    if rank == 23:
        record['documentation_urls'].append('https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html')
    if rank == 46:
        record['notes'].append('Seven named UCSC utilities sampled; package list is not exhaustive.')
    if rank in {16, 22, 41, 46}:
        record['notes'].append('One repository entry; package counters retained separately and not interpreted as unique users.')
    records.append(record)

for name, package, purpose, role in extra_conda:
    info = recipe(package)
    repository = info.get('dev_url')
    if not repository and info.get('home', '').startswith(('https://github.com/', 'https://gitlab.com/')):
        repository = info['home']
    if package == 'viennarna':
        repository = 'https://github.com/ViennaRNA/ViennaRNA'
    record = candidate(name, repository, purpose, role, [package])
    if package in {'meme', 'entrez-direct'}:
        record['source_access'] = 'source distribution identified; public repository unresolved'
        record['notes'].append('Keep as a software lead; do not count as a resolved repository.')
    records.append(record)

for package, purpose, role in extra_bioc:
    record = candidate(package, None, purpose, role, ['bioconductor-'+package.lower()], package)
    if package == 'scuttle':
        record['notes'].append('Current release describes the package as legacy; assess current replacements before extraction.')
    records.append(record)

for record in records:
    if record['role'] == 'workflow infrastructure':
        record['notes'].append('Discovery route to scientific workflow repositories; orchestration itself is not biological analysis.')
    if record['role'] == 'retrieval tool':
        record['notes'].append('Inspect bounded data sources and offline staging requirements.')
    if record['role'] == 'visualization tool':
        record['notes'].append('Inspect underlying numerical artifacts and whether an executable grading contract is useful.')
    if record['role'] == 'scientific library':
        record['notes'].append('Downloads can be driven by downstream dependencies; inspect scientific call sites.')

assert len(records) == 95
resolved = [record['repository_url'].rstrip('/').lower() for record in records if record['repository_url']]
assert len(set(resolved)) == len(resolved)
assert len([record for record in records if record['previous_inventory_rank']]) == 50
assert all('{{' not in url for record in records for url in record['documentation_urls'])

sources = [
    {'id': 'bioconda-downloads',
     'url': f'https://github.com/bioconda/bioconda-stats/blob/{STATS_REVISION}/package-downloads/anaconda.org/bioconda/packages.tsv',
     'revision': STATS_REVISION, 'as_of': '2026-09-29', 'rows': len(conda_counts),
     'metric': 'Cumulative file downloads for main-label conda artifacts, aggregated across versions, builds and platforms.',
     'sha256': hashlib.sha256((ROOT/'bioconda-packages.tsv').read_bytes()).hexdigest()},
    {'id': 'bioconductor-scores', 'url': 'https://www.bioconductor.org/packages/stats/bioc/bioc_pkg_scores.tab',
     'as_of': '2026-09-28', 'rows': len(bioc_scores),
     'metric': 'Average monthly distinct IPs during the previous 12 complete months; not a 12-month unique-user count.',
     'period_start': '2025-09-01', 'period_end': '2026-08-31',
     'sha256': hashlib.sha256((ROOT/'bioconductor-scores.tsv').read_bytes()).hexdigest()},
    {'id': 'bioconductor-metadata', 'url': 'https://bioconductor.org/packages/3.23/bioc/VIEWS',
     'retrieved_url': 'https://bioconductor.org/packages/release/bioc/VIEWS', 'release': '3.23',
     'sha256': hashlib.sha256((ROOT/'bioconductor-VIEWS').read_bytes()).hexdigest()},
    {'id': 'bioconda-recipes', 'url': f'https://github.com/bioconda/bioconda-recipes/tree/{BIOCONDA_REVISION}/recipes',
     'revision': BIOCONDA_REVISION},
    {'id': 'previous-inventory', 'url': PRIOR_URL, 'metrics_as_of': '2026-07-28'},
]
result = {'observed_on': '2026-09-29', 'sources': sources, 'repositories': records,
          'unresolved_adoption_leads': [
              {'package': package, 'bioconda_cumulative_downloads': conda_counts[package],
               'status': 'Scientific purpose and independent adoption not inspected; count alone does not justify selection.'}
              for package in ['harpy', 'genenotebook', 'genoboo']],
          'metric_limitations': [
              'A recent-window Bioconda download count has not been computed.',
              'Bioconda counters omit other channels and distribution methods and include automated and dependency downloads.',
              'Bioconductor IP scores and Bioconda cumulative counts must not be added or ranked together.',
              'No packages were installed and no candidate execution or input-data redistribution was validated.',
          ]}
(ROOT/'inventory-draft.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
print('entries', len(records), 'resolved_repositories', len(resolved), 'new_entries', sum(r['previous_inventory_rank'] is None for r in records))
print('missing_counts', [(r['name'], p['name']) for r in records for p in r['bioconda_packages'] if p['cumulative_downloads'] is None])
