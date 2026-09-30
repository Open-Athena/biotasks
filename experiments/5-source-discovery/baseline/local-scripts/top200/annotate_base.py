"""Materialize explicit source-by-source judgments; no inferred keyword labels."""
import json
from pathlib import Path

ROOT=Path('/tmp/bio-discovery-20260929/top200')
data=json.loads((ROOT/'cohorts-provisional.json').read_text())
sources={r['source_id']:r for r in data['sources']}
short={}
for key in sources:
    name=key.rsplit('/',1)[-1].split(':')[-1]
    if name in short:
        previous=short.pop(name)
        short[previous.removeprefix('github:')]=previous
        name=key.removeprefix('github:')
    short[name]=key
annotations={}

def group(domain,topic,names):
    for name in names.split():
        if name not in short:continue
        key=short[name]
        assert key not in annotations,key
        annotations[key]={'primary_domain':domain,'manual_topic':topic,'source_type':'Software','scope_note':''}

# Explicit review assignments from package summaries, repository descriptions,
# Bioconductor titles/biocViews, and selected README inspection.
group('Sequence processing','Alignment files and sequencing formats','pysam samtools htslib picard rsamtools genomicalignments dnaio rhtslib pyfaidx bamtools shortread cigarillo biocommons.seqrepo')
group('Sequence processing','Read and sequence alignment','bowtie2 last bwa minimap2 bowtie star edlib')
group('Sequence processing','Sequence similarity and alignment','ncbi-cxx-toolkit-public diamond hmmer mmseqs2 mafft muscle pwalign pyhmmer pyfamsa')
group('Sequence processing','Read processing and quality control','bbtools cutadapt fastqc seqkit seqtk fastp multiqc sortmerna')
group('Sequence processing','Sequence manipulation','biostrings bx-python bioutils')
group('Sequence processing','Sequencing archive access','sra-tools ncbi-vdb')
group('Genome assembly & annotation','Genomic intervals and coordinates','bedtools2 genomicranges pybedtools genomeinfodb seqinfo rtracklayer kent pyranges0 ncls')
group('Genome assembly & annotation','Genome assembly','spades abyss unicycler')
group('Genome assembly & annotation','Gene prediction and genome annotation','augustus annotationdbi annotate genomicfeatures annotationfilter ensembldb bsgenome pyrodigal')
group('Genome assembly & annotation','Genome reference access','biomart ucsc.utils gget genomeinfodbdata')
group('Genome assembly & annotation','Comparative genome browsing','genenotebook genoboo')
group('Genetic variation','Variant formats and annotation','bcftools cyvcf2 snpeff variantannotation')
group('Genetic variation','Variant calling and phasing','gatk freebayes harpy deepvariant')
group('Genetic variation','Association and population genetics','vcftools saige bed-reader pysnptools')
group('Genetic variation','Pangenome graphs','vg')
group('Gene expression','Bulk differential expression','limma deseq2 edger genefilter enhancedvolcano glmgampoi apeglm metapod')
group('Gene expression','Expression quantification and transcript assembly','htseq stringtie salmon')
group('Gene expression','Microarray processing and normalization','preprocesscore impute affyio affy vsn')
group('Gene expression','Batch effect adjustment','sva')
group('Gene expression','Expression data access','geoquery')
group('Gene expression','Ribosome profiling','rust')
group('Single-cell & spatial omics','Single-cell containers and storage','singlecellexperiment anndata mudata tiledb-soma spatialexperiment')
group('Single-cell & spatial omics','Single-cell analysis and annotation','scuttle scater scran singler scanpy seurat scvi-tools scgpt')
group('Single-cell & spatial omics','Single-cell preprocessing','harmonypy scrublet')
group('Single-cell & spatial omics','Spatial expression analysis','squidpy')
group('Single-cell & spatial omics','Single-cell atlases and resource discovery','cellxgene-census awesome-single-cell')
group('Gene regulation','Sequence motifs and visualization','meme-5.5.9.tar.gz logomaker')
group('Gene regulation','Chromatin signal processing','deeptools pybigwig')
group('Gene regulation','Regulatory sequence modeling','alphagenome')
group('Phylogenetics & evolution','Phylogenetic inference','fasttree standard-raxml iqtree3 sepp hyphy treetime')
group('Phylogenetics & evolution','Phylogenetic trees and visualization','dendropy treeio ggtree ete')
group('Microbiome & metagenomics','Community profiling and diversity','vsearch dada2 unifrac phyloseq')
group('Microbiome & metagenomics','Community observation formats','biomformat biom-format')
group('RNA structure','RNA folding','viennarna')
group('Proteomics','Mass spectrometry analysis','peptide-shaker searchgui pyteomics openms pymzml')
group('Proteomics','Mass spectrometry interfaces','protgenerics')
group('Protein structure & biophysics','Molecular structures and visualization','gemmi mrcfile 3dmol.js tmtools ccdutils pdb-tools nglview pymol-open-source molecularnodes graphein hydride')
group('Protein structure & biophysics','Molecular simulation and trajectory analysis','mdanalysis mdtraj packmol pymbar openmm lammps jax-md')
group('Protein structure & biophysics','Protein structure search','foldseek')
group('Protein structure & biophysics','Protein models and design','alphafold alphafold3 esm proteinmpnn alphafold3-pytorch prottrans aice bindcraft colabfold')
group('Protein structure & biophysics','Protein modeling literature','papers_for_protein_design_using_dl machine-learning-for-proteins')
group('Cheminformatics & drug discovery','Molecular representations and descriptors','rdkit pubchempy openbabel chematic descriptastorus datamol indigo')
group('Cheminformatics & drug discovery','Molecular docking','meeko autodock-vina diffdock')
group('Cheminformatics & drug discovery','Molecular property and interaction prediction','chemprop deepchem graphormer deeppurpose tdc')
group('Cheminformatics & drug discovery','Cheminformatics instruction','practical_cheminformatics_tutorials')
group('Bioimaging','Biological and medical image analysis','openslide-python nnunet connected-components-3d napari cellpose trackpy slicer nitrain pyradiomics dltk cellprofiler')
group('Bioimaging','Image metadata and plugins','ome-types napari-plugin-engine')
group('Bioimaging','Biomedical imaging datasets','medmnist')
group('Bioimaging','Microscopy hardware','microscopy')
group('Neuroscience & behavior','Neural recording and signal analysis','mne-python pynwb neurokit python-neo brainflow braindecode')
group('Neuroscience & behavior','Neuroimaging','nibabel nilearn nipype pybids ants dcm2niix')
group('Neuroscience & behavior','Behavior and experimental psychology','deeplabcut psychopy')
group('Neuroscience & behavior','Neural simulation','openworm brian2')
group('Neuroscience & behavior','Neuroscience teaching and resources','course-content awesome-neuroscience')
group('Systems biology & ontologies','Pathway and gene-set analysis','keggrest enrichplot fgsea clusterprofiler gseabase gsva kegggraph graphite reactomepa gseapy gprofiler-official-1.0.0.tar.gz')
group('Systems biology & ontologies','Biological identifiers and ontologies','prefixcommons-py prefixmaps fastobo-py pronto sssom-py ols-client bioregistry biothings_client.py mygene.py dose gosemsim')
group('Systems biology & ontologies','Biological networks and metabolism','ndex2-client omnipath cobrapy')
group('Biomedical text & clinical data','Biomedical language processing','negspacy biobert scispacy')
group('Biomedical text & clinical data','Clinical data integration','client-py mirobody')
group('Biomedical text & clinical data','Medical research instructions','medical-research-skills')
group('General biology & multi-omics','General biological analysis libraries','biopython biotite scikit-bio rust-bio')
group('General biology & multi-omics','Biological database access','edirect.tar.gz eutils annotationhub experimenthub')
group('General biology & multi-omics','Multi-omics integration','multiassayexperiment omicverse tcgabiolinks')
group('General biology & multi-omics','Genomic foundation models','evo')
group('General biology & multi-omics','Experimental primer design','primer3-py')
group('General biology & multi-omics','Flow cytometry formats','flowio')
group('General biology & multi-omics','Biological teaching and discovery resources','bioinformatics awesome-bioinformatics deeplearning-biology oneliners awesome-deepbio learning-bioinformatics-at-home getting-started-with-genomics-tools-and-resources training-collection applied-computational-genomics')
group('General biology & multi-omics','Biology and medicine review','deep-review')
group('General biology & multi-omics','Biological agent instructions','scientific-agent-skills bioskills clawbio')
group('Computing infrastructure','Bioconductor containers and operations','s4vectors biocgenerics iranges biobase xvector delayedarray summarizedexperiment matrixgenerics sparsearray s4arrays beachmat sparsematrixstats delayedmatrixstats biocsingular scaledmatrix biocneighbors bluster')
group('Computing infrastructure','Scientific storage and I/O','zlibbioc rhdf5 rhdf5lib rhdf5filters hdf5array h5mread biocio')
group('Computing infrastructure','Bioinformatics workflow platforms','snakemake nextflow cwltool cwl-upgrader dx-toolkit bioblend galaxy')
group('Computing infrastructure','Parallel computing and package infrastructure','biocparallel bioconda-recipes biocversion biocfilecache assorthead biocbaseutils dir.expiry biocstyle')
group('Computing infrastructure','Statistics and visualization for biology','qvalue graph rgraphviz rbgl multtest pcamethods complexheatmap biovizbase')

group('Bioimaging','Medical image segmentation','medsam seglossodyssey transunet ssl4mis unetplusplus swin-unet 3dunetcnn attention-gated-networks medicalzoopytorch sota-medseg')
group('Bioimaging','Image processing and viewing','viewers torchio cornerstone dwv itk qupath')
group('Bioimaging','Medical imaging resources','dataset medical-imaging-datasets awesome-gan-for-medical-imaging awesome-diffusion-models-in-medical-imaging deep-learning-for-medical-applications')
group('Bioimaging','MRI reconstruction','fastmri')
group('Protein structure & biophysics','Biomolecular interaction modeling','boltz')
group('Cheminformatics & drug discovery','Drug discovery machine learning','torchdrug')
group('General biology & multi-omics','Biomedical agent platform','biomni')
group('Biomedical text & clinical data','Medical AI resources','awesome-ai4med')
group('Single-cell & spatial omics','Single-cell analysis instruction','single-cell-tutorial')

def types(kind,names):
    for name in names.split():
        if name in short:annotations[short[name]]['source_type']=kind

# Classify the repository's main deliverable; embedded tutorials do not change
# a software repository into a course. Biology-specific infrastructure remains
# eligible, with its biological domain separate from this source-type axis.
types('Infrastructure','s4vectors biocgenerics iranges biobase xvector delayedarray summarizedexperiment matrixgenerics sparsearray s4arrays beachmat sparsematrixstats delayedmatrixstats biocsingular scaledmatrix biocneighbors bluster zlibbioc rhdf5 rhdf5lib rhdf5filters hdf5array h5mread biocio snakemake nextflow cwltool cwl-upgrader dx-toolkit bioblend galaxy biocparallel bioconda-recipes biocversion biocfilecache assorthead biocbaseutils dir.expiry biocstyle graph rbgl rgraphviz singlecellexperiment anndata mudata tiledb-soma spatialexperiment multiassayexperiment protgenerics ome-types napari-plugin-engine htslib rhtslib ncbi-vdb')
types('Workflow','harpy deepvariant unicycler colabfold bindcraft nipype')
types('Research implementation','alphafold alphafold3 esm proteinmpnn alphafold3-pytorch prottrans aice graphormer diffdock evo scgpt biobert')
types('Tutorial/course','course-content oneliners getting-started-with-genomics-tools-and-resources practical_cheminformatics_tutorials applied-computational-genomics')
types('Resource index','bioinformatics awesome-bioinformatics deeplearning-biology awesome-deepbio learning-bioinformatics-at-home training-collection papers_for_protein_design_using_dl machine-learning-for-proteins awesome-neuroscience awesome-single-cell')
types('Agent instructions','scientific-agent-skills medical-research-skills bioskills clawbio')
types('Data resource','genomeinfodbdata medmnist')
types('Review/article','deep-review')
types('Hardware project','microscopy')
types('Research implementation','medsam transunet unetplusplus swin-unet attention-gated-networks boltz')
types('Resource index','dataset medical-imaging-datasets awesome-gan-for-medical-imaging awesome-diffusion-models-in-medical-imaging deep-learning-for-medical-applications awesome-ai4med')
types('Tutorial/course','single-cell-tutorial')
notes={
 'scientific-agent-skills':'Cross-science collection retained for substantial original biological instructional content. Biological subset needs later inspection; repository stars cover the full collection.',
 'lammps':'Broad molecular/materials engine retained because official model documentation explicitly includes proteins and DNA; all repository stars cover the broader project.',
 'jax-md':'Broad condensed-matter engine retained with documented protein-design applications; borderline scope. See README cited intrinsically disordered protein design work.',
 'graphormer':'Broad molecular modeling retained for explicit drug-discovery scope; materials applications also present.',
 'trackpy':'Broad particle-tracking tool retained in bioimaging; biological task examples still need inspection. Borderline scope.',
 'prefixmaps':'Cross-domain semantic utility retained for documented OBO, CHEBI and GEO identifier workflows. Borderline scope.',
 'prefixcommons-py':'Identifier utility retained for documented Gene Ontology and biocontext usage.',
 'sssom-py':'General ontology mapping format retained for documented phenotype-ontology mapping example. Borderline scope.',
 'ncls':'General interval structure retained as an explicit PyRanges bioinformatics component; not counted as a new analysis subdomain.',
 'connected-components-3d':'README explicitly identifies densely labeled biomedical brain tissue as its originating use case.',
 'bioconda-recipes':'Distribution and installation recipes. Package score is for the Bioconductor data-package helper, not the whole repository.',
 'genoboo':'Maintained fork of GeneNotebook; retained as a distinct source identity, without claiming a distinct biological topic.',
 'flowio':'Flow cytometry is a separate manual topic within the broad general-biology primary domain.',
 'evo':'Genome and molecular sequence modeling spans several biological domains; broad primary label avoids treating it as a protein-only tool.',
 'tcgabiolinks':'Cancer multi-omics data access/analysis; cancer is recorded in the source description rather than used as a separate organ-specific taxonomy axis.',
 'genomeinfodbdata':'Bioconductor annotation-data package, distinct from software package GenomeInfoDb.',
 'biotite':'General molecular-biology library spans sequence, structure and simulation; primary label is deliberately broad.',
 'phyloseq':'Microbial ecology is included in the microbiome domain; this does not establish coverage of general ecological modeling.',
 'pyranges0':'The package metadata resolves to pyranges/pyranges0; retain that identity rather than substituting a newer rewrite.',
}
for name,note in notes.items():
 if name in short:annotations[short[name]]['scope_note']=note
missing=set(sources)-set(annotations)
print('Unclassified:',len(missing))
for key,a in annotations.items():
 r=sources[key]
 a['source_id']=key
 a['evidence_urls']=r['evidence_urls']
 a['evidence_summary']=r['summary']
 if key.startswith('github:'):
  name=key.removeprefix('github:').replace('/','__')
  f=ROOT/'readmes'/(name+'.json')
  if f.exists():
   readme=json.loads(f.read_text());a['evidence_urls']=[readme['html_url']]+a['evidence_urls']
 a['annotation_method']='assistant manual metadata review; selected README checks; not independently human-validated'
(ROOT/'annotations.json').write_text(json.dumps([annotations[k] for k in sorted(annotations)],indent=2)+'\n')
print('Annotated',len(annotations),'unique sources')
