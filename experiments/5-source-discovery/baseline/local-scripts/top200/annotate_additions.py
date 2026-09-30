"""Explicit manual review of additional selected sources; retain baseline judgments."""
import json
from pathlib import Path
r=Path('/tmp/bio-discovery-20260929/top200')
data=json.loads((r/'cohorts-provisional.json').read_text());sources={s['source_id']:s for s in data['sources']}
a={x['source_id']:x for x in json.loads((r/'annotations.json').read_text())}
# The original annotations, including scope notes, remain byte-for-byte equivalent as values.
baseline={x['source_id']:x for x in json.loads((r.parent/'top100/annotations.json').read_text())};a.update(baseline)
short={}
for key in sources:
 n=key.rsplit('/',1)[-1].split(':')[-1]
 if n=='decoupler':n=key.removeprefix('github:')
 assert n not in short,(n,key)
 short[n]=key

def group(domain,topic,names):
 for name in names.split():
  assert name in short,name
  key=short[name];assert key not in a,key
  a[key]={'source_id':key,'primary_domain':domain,'manual_topic':topic,'source_type':'Software','scope_note':''}

group('Sequence processing','Alignment files and sequencing formats','sambamba bio-samtools-1.43.tar.gz slow5tools fgbio scoring-matrices pyfastx')
group('Sequence processing','Read and sequence alignment','gmap-gsnap-2025-07-31.tar.gz hisat2 subread-2.1.1-source.tar.gz rsubread')
group('Sequence processing','Sequence similarity and alignment','clustalw-2.1.tar.gz parasail-python kalign clustal-omega-1.2.4.tar.gz bio-tools-run-alignment-clustalw-1.7.4.tar.gz bio-tools-run-alignment-tcoffee-1.7.4.tar.gz decipher msa')
group('Sequence processing','Read processing and quality control','trimmomatic trimgalore')
group('Sequence processing','Sequence manipulation','rust-bio-tools')
group('Genome assembly & annotation','Gene prediction and genome annotation','genometools prodigal trnascan-se prokka txdbmaker organismdbi annotationforge gffutils gtfparse jcvi')
group('Genome assembly & annotation','Genomic intervals and coordinates','bio-coordinate-1.007001.tar.gz bio-featureio-1.6.905.tar.gz pyliftover bioframe sorted_nearest')
group('Genome assembly & annotation','Genome assembly','megahit medaka')
group('Genome assembly & annotation','Assembly and annotation quality assessment','busco quast')
group('Genome assembly & annotation','Genome reference access','pyensembl genomepy refgenie ncbi-genome-download')
group('Genome assembly & annotation','Genome track visualization','gviz ggbio pygenometracks pycirclize')
group('Genetic variation','Gene fusion detection','star-fusion')
group('Genetic variation','Variant formats and annotation','pyvcf3 ensembl-vep snpsift hgvs varcode isovar maftools')
group('Genetic variation','Variant calling and phasing','vardictjava varlociraptor bcbio-nextgen')
group('Genetic variation','Association and population genetics','stacks-2.68.tar.gz snpstats snprelate hail')
group('Genetic variation','Copy-number analysis','dnacopy infercnv')
group('Genetic variation','Ancestry and population simulation','tskit msprime')
group('Genetic variation','Association and risk-score instruction','gwa_tutorial')
group('Gene expression','Expression quantification and transcript assembly','trinityrnaseq kallisto tximport tximeta')
group('Gene expression','Bulk differential expression','siggenes')
group('Gene expression','Microarray processing and normalization','illuminaio oligo affxparser marray aroma.light')
group('Gene expression','Expression normalization and variation','variancepartition wrench edaseq')
group('Gene expression','Differential exon usage','dexseq')
group('Gene expression','Expression data access','geoparse')
group('Single-cell & spatial omics','Single-cell preprocessing','batchelor scdblfinder dropletutils')
group('Single-cell & spatial omics','Single-cell analysis and annotation','mast scrapper sccoord-1.6.100.tar.gz')
group('Single-cell & spatial omics','Cell trajectories and differentiation','monocle trajectoryutils slingshot palantir')
group('Single-cell & spatial omics','Single-cell gene-set activity','aucell ucell')
group('Single-cell & spatial omics','Single-cell containers and storage','zellkonverter loompy')
group('Single-cell & spatial omics','Spatial expression analysis','starfish')
group('Single-cell & spatial omics','Single-cell analysis instruction','single-cell-best-practices')
group('Gene regulation','Sequence motifs and visualization','tfbstools seqlogo motifmatchr memesuite-lite pyjaspar')
group('Gene regulation','Chromatin signal processing','chipseeker bigtools')
group('Gene regulation','Chromosome conformation','cooltools cooler interactionset')
group('Gene regulation','Regulatory sequence modeling','tangermeme ledidi bpnet-lite')
group('Gene regulation','DNA methylation','bumphunter minfi bsseq methylumi')
group('Gene regulation','Regulatory element conservation and enrichment','cner regioner')
group('General biology & multi-omics','Genome editing and off-target analysis','crisprme')
group('General biology & multi-omics','Experimental primer design','primer3')
group('General biology & multi-omics','General biological analysis libraries','bioperl-1.7.8.tar.gz bioperl-run-1.007003.tar.gz bcbb')
group('General biology & multi-omics','Biological database access','bio-asn1-entrezgene-1.73.tar.gz bioversions')
group('General biology & multi-omics','Multi-omics integration','mixomics multidataset cbioportal')
group('General biology & multi-omics','Flow cytometry formats','flowcore cytolib flowworkspace fcsparser')
group('General biology & multi-omics','Cell mechanics and cytometry','dclab')
group('General biology & multi-omics','Genomic foundation models','nucleotide-transformer')
group('General biology & multi-omics','Biological teaching and discovery resources','an-introduction-to-applied-bioinformatics')
group('Microbiome & metagenomics','Community profiling and diversity','deblur prophyle metaphlan gneiss unifrac-binaries mash sourmash dirichletmultinomial microbiome mia ancombc metagenomeseq kraken2')
group('Microbiome & metagenomics','Microbial contamination detection','decontam')
group('Microbiome & metagenomics','Microbial typing and pathogen detection','mlst thapbi-pict')
group('Phylogenetics & evolution','Phylogenetic inference','paml bio-tools-phylo-paml-1.7.3.tar.gz')
group('Phylogenetics & evolution','Phylogenetic trees and visualization','improved-octo-waddle treesummarizedexperiment ggtreeextra')
group('Phylogenetics & evolution','Pathogen evolution and surveillance','pango-designation augur')
group('RNA structure','RNA homology and covariance models','infernal')
group('Proteomics','Mass spectrometry analysis','comet msnbase qfeatures psmatch massspecwavelet msfeatures matchms')
group('Proteomics','Mass spectrometry interfaces','mzr mscoreutils mzid spectra')
group('Proteomics','Affinity proteomics data formats','canopy')
group('Protein structure & biophysics','Protein homology and domain annotation','hh-suite rpsbproc-src.tar.gz')
group('Protein structure & biophysics','Molecular structures and visualization','libcifpp py-rcsb-api mmcif_pdbx biopandas')
group('Protein structure & biophysics','Molecular simulation and trajectory analysis','prody alchemlyb parmed gromacs')
group('Protein structure & biophysics','Protonation and electrostatic preparation','propka pdb2pqr')
group('Protein structure & biophysics','Protein models and design','tmol boltzgen colabdesign')
group('Protein structure & biophysics','Structure modeling evaluation and data','dockq proteinnet')
group('Immunology','Immune receptor annotation','anarci mhcgnomes')
group('Immunology','Antigen presentation and vaccine peptides','mhctools topiary hitlist vaxrank')
group('Metabolomics','Metabolomics processing and statistics','metabocoreutils xcms ropls')
group('Ecology & conservation','Wildlife monitoring and conservation resources','biodiversity')
group('Biomechanics & physiology','Musculoskeletal simulation','opensim-core')
group('Cheminformatics & drug discovery','Molecular representations and descriptors','prolif e3fp scikit-fingerprints mol_hume-1.0.1.tar.gz morfeus molmass ketcher dimorphite_dl')
group('Cheminformatics & drug discovery','Molecular docking','posebusters gnina')
group('Cheminformatics & drug discovery','Molecular generation evaluation','moses')
group('Cheminformatics & drug discovery','Retrosynthetic planning','aizynthfinder')
group('Cheminformatics & drug discovery','Molecular design literature','papers-for-molecular-design-using-dl')
group('Systems biology & ontologies','Pathway and gene-set analysis','pathview topgo singscore globaltest goatools')
group('Systems biology & ontologies','Biological identifiers and ontologies','obonet biolink-model biolink-model-toolkit bionty')
group('Systems biology & ontologies','Biological networks and metabolism','stringdb')
group('Systems biology & ontologies','Biological activity inference','saezlab/decoupler scverse/decoupler')
group('Systems biology & ontologies','Biochemical reaction and diffusion simulation','smoldyn')
group('Bioimaging','Biological and medical image analysis','ebimage centrosome niftynet antspy')
group('Bioimaging','Image metadata and plugins','napari-plugin-manager ngff-zarr bioio aicspylibczi fo-dicom dicom')
group('Bioimaging','Image processing and viewing','weasis cornerstone3d ctk')
group('Bioimaging','Medical image segmentation','medsegdiff medical-sam-adapter deepmedic msnet-m2snet u-mamba sam-med3d medical-sam2')
group('Bioimaging','Image labeling and annotation','monailabel')
group('Bioimaging','Medical image detection and classification','medicaldetectiontoolkit torchxrayvision breast_cancer_classifier')
group('Bioimaging','Medical image reasoning','medrax')
group('Bioimaging','Optical tomography','acoustooptictomography')
group('Bioimaging','Medical imaging resources','awesome-transformers-in-medical-imaging miccai-opensourcepapers sam4mis awesome-multimodal-in-medical-imaging medical-datasets')
group('Bioimaging','Microscopy hardware','legomicroscope')
group('Neuroscience & behavior','Neural recording and signal analysis','fooof elephant fieldtrip')
group('Neuroscience & behavior','Neural data access','dandi-cli')
group('Neuroscience & behavior','Neuroimaging','transformnd neuroharmonize python-client')
group('Neuroscience & behavior','Neural simulation','nengo')
group('Neuroscience & behavior','Brain-computer interface evaluation','moabb')
group('Neuroscience & behavior','Neuroscience teaching and resources','awesome-neural-geometry awesome-computational-neuroscience')
group('Biomedical text & clinical data','Biomedical language processing','quickumls drug_named_entity_recognition medical_named_entity_recognition kg_rag')
group('Biomedical text & clinical data','Biomedical literature access','metapub')
group('Biomedical text & clinical data','Biomedical agent platform','multi-agent-medical-assistant biomcp')
group('Computing infrastructure','Bioconductor containers and operations','residualmatrix')
group('Computing infrastructure','Scientific storage and I/O','alabaster.base alabaster.matrix alabaster.ranges alabaster.se alabaster.schemas gypsum-r gdsfmt lamindb datacache crypt4gh')
group('Computing infrastructure','Bioinformatics workflow platforms','snakemake-interface-common snakemake-interface-executor-plugins snakemake-interface-storage-plugins snakemake-interface-report-plugins snakemake-interface-logger-plugins cg pypiper scipipe cromwell adam toil tools')
group('Computing infrastructure','Parallel computing and package infrastructure','bioconda-utils biocviews biocmake basilisk basilisk.utils bioccheck rprotobuflib')
group('Computing infrastructure','Statistics and visualization for biology','geneplotter consensusclusterplus interactivedisplaybase tkwidgets widgettools marsilea')
group('Computing infrastructure','Experiment metadata and data sharing','pephubclient isa-rwval synapsepythonclient')
group('Gene expression','Microarray containers','oligoclasses')

def types(kind,names):
 for name in names.split():
  key=short[name];assert key not in baseline,key;a[key]['source_type']=kind

types('Infrastructure','snakemake-interface-common snakemake-interface-executor-plugins snakemake-interface-storage-plugins snakemake-interface-report-plugins snakemake-interface-logger-plugins bioconda-utils biocviews biocmake basilisk basilisk.utils bioccheck rprotobuflib residualmatrix alabaster.base alabaster.matrix alabaster.ranges alabaster.se alabaster.schemas gypsum-r gdsfmt lamindb datacache crypt4gh cg pypiper scipipe cromwell adam toil tools pephubclient isa-rwval synapsepythonclient tkwidgets widgettools interactivedisplaybase sorted_nearest napari-plugin-manager zellkonverter loompy flowcore cytolib flowworkspace treesummarizedexperiment oligoclasses multidataset spectra mscoreutils ngff-zarr fo-dicom dicom ctk biolink-model')
types('Workflow','bcbio-nextgen trimgalore augur colabdesign')
types('Research implementation','boltzgen nucleotide-transformer medsegdiff medical-sam-adapter medrax deepmedic msnet-m2snet u-mamba sam-med3d medical-sam2 breast_cancer_classifier kg_rag')
types('Resource index','biodiversity awesome-transformers-in-medical-imaging miccai-opensourcepapers sam4mis awesome-multimodal-in-medical-imaging medical-datasets awesome-neural-geometry awesome-computational-neuroscience papers-for-molecular-design-using-dl')
types('Tutorial/course','single-cell-best-practices gwa_tutorial an-introduction-to-applied-bioinformatics')
types('Data resource','pango-designation hitlist proteinnet')
types('Hardware project','legomicroscope')
notes={
'biodiversity':'Current README is a conservation-project hub linking to separately maintained detector, acoustic and wildlife repositories. Count as a resource index; downstream repositories are not added to this frozen ranking.',
'legomicroscope':'Educational microscope construction project with build instructions; hardware is its main deliverable.',
'genometools':'Genome annotation and sequence-analysis toolkit; same source as Bioconda genometools-genometools.',
'bioperl-1.7.8.tar.gz':'Collapse the BioPerl metapackage and BioPerl core package to the pinned official BioPerl source distribution; maximum counter, not sum.',
'medaka':'Both nanopore consensus polishing and variant calling; assembly/polishing is the primary label.',
'crisprme':'Genome-editing design is a new finer topic under the established broad general-biology group.',
'improved-octo-waddle':'General tree representation retained for explicit jplace phylogenetic fragment-insertion functionality.',
'unifrac-binaries':'Contains the native C++ UniFrac implementation; distinct from the independently maintained Python interface repository in the first hundred.',
'datacache':'General caching utility retained as dedicated OpenVax/PyEnsembl ecosystem support; borderline, classified as infrastructure.',
'centrosome':'CellProfiler image-processing dependency; retained as bioimaging support without claiming a distinct scientific subdomain.',
'transformnd':'General coordinate-transform interface retained as a documented component derived from the NAVIS neuroanatomy ecosystem; borderline.',
'marsilea':'General composable plotting with documented single-cell and gene-expression examples; same treatment as ComplexHeatmap.',
'molmass':'Cross-domain molecular chemistry utility; retained alongside molecular descriptor tools, not treated as a distinct biological subdomain.',
'morfeus':'Cross-domain molecular descriptors and steric/electronic properties; chemical catalyst applications also present.',
'aizynthfinder':'Cross-domain synthesis planning; retained in cheminformatics/drug discovery. A novel finer analysis activity, not a new organism or biology field.',
'papers-for-molecular-design-using-dl':'Mixed molecular and materials design literature index; substantial molecular design coverage, with full-repository stars.',
'awesome-neural-geometry':'Spans computational neuroscience and general representation geometry; substantial explicit neuroscience resources.',
'nengo':'Biologically motivated brain modeling and cognitive simulation; distinct from excluded general spiking-neural-network training frameworks.',
'sccoord-1.6.100.tar.gz':'Current PyPI GitHub link did not resolve; retain the official PyPI source archive and package description. Repository topics are unavailable.',
'fcsparser':'Current PyPI project_urls incorrectly point to eyurtsev/kor. The package description links its worked example and documentation to eyurtsev/fcsparser.',
'quickumls':'Use the maintained medspacy/QuickUMLS fork named in the package description, not the stale upstream homepage.',
'ropls':'Multivariate omics methods with metabolomics use; primary assignment is metabolomics, but methods also apply to other omics.',
'gromacs':'GitHub is the official public backup; development and issues use the linked GitLab repository. Keep the observed GitHub identity for this star ranking.',
'biomcp':'Dedicated biomedical database interface retained; distinguished from general scientific agent runtimes.',
}
for name,note in notes.items():a[short[name]]['scope_note']=note
missing=set(sources)-set(a)
if missing:
 print('MISSING',len(missing))
 for key in sorted(missing):print(key,sources[key]['summary'])
 raise SystemExit(1)
for key,x in a.items():
 if key in baseline:continue
 s=sources[key];x['evidence_urls']=s['evidence_urls'];x['evidence_summary']=s['summary'];x['annotation_method']='assistant manual metadata review; selected README checks; not independently human-validated'
 if key.startswith('github:'):
  f=r/'readmes'/(key[7:].replace('/','__')+'.json')
  if f.exists():x['evidence_urls']=[json.loads(f.read_text())['html_url']]+x['evidence_urls']
assert all(a[k]==v for k,v in baseline.items())
(r/'annotations.json').write_text(json.dumps([a[k] for k in sorted(a)],indent=2)+'\n')
print('Annotated',len(a),'sources;',len(a)-len(baseline),'new to all four baseline lists')
