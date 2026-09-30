import datetime
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path('/tmp/bio-discovery-20260929')
REVISION = '254ba2d4bcda7fe6ed2baa586bac6c35885a4b10'
PACKAGES = '''blast samtools bwa bowtie2 star bedtools gatk4 pysam mafft hmmer minimap2 bcftools picard snakemake snakemake-minimal htslib fastqc biopython nextflow diamond plink plink2 scanpy multiqc spades iqtree fasttree raxml cutadapt salmon kallisto stringtie fastp sra-tools deeptools vcftools snpeff ensembl-vep macs2 macs3 mmseqs2 muscle kraken2 busco pybedtools nf-core last meme bbmap entrez-direct viennarna hyphy sepp htseq vsearch freebayes seqkit seqtk searchgui peptide-shaker prokka quast checkm-genome mash sourmash bedops bamtools pybigwig pyfaidx cyvcf2 dendropy ucsc-liftover ucsc-bedgraphtobigwig ucsc-bigwigtobedgraph ucsc-fatotwobit ucsc-twobittofa ucsc-bedtobigbed ucsc-bigbedtobed'''.split()

def resources(start=False):
    mem = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))) * 1024
    load = os.getloadavg()[0]
    if start:
        assert mem >= 2.5*1024**3 and mem-100*1024**2 >= 2*1024**3 and load < 1.5, (mem, load)
    elif mem < 2*1024**3 or load > 2.5:
        raise RuntimeError(f'Node resource threshold reached: {mem=}, {load=}')

resources(start=True)
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated working set 100 MiB', flush=True)
(ROOT/'recipes').mkdir(exist_ok=True)
receipts=[]
for index, package in enumerate(PACKAGES):
    resources()
    url=f'https://raw.githubusercontent.com/bioconda/bioconda-recipes/{REVISION}/recipes/{package}/meta.yaml'
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload=response.read(512*1024+1)
        assert len(payload)<=512*1024, package
        (ROOT/'recipes'/f'{package}.yaml').write_bytes(payload)
        receipts.append({'package':package,'url':url,'status':'ok','bytes':len(payload)})
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        receipts.append({'package':package,'url':url,'status':'missing recipe'})
    if (index+1)%10==0:
        print('fetched',index+1,'of',len(PACKAGES), flush=True)
(ROOT/'recipe-fetch.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('end',datetime.datetime.now(datetime.UTC).isoformat(), 'recipes',len(receipts), 'missing',[r['package'] for r in receipts if r['status']!='ok'], flush=True)
