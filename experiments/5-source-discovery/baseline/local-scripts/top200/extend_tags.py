import json
from pathlib import Path
r=Path('/tmp/bio-discovery-20260929/top200');m=json.loads((r.parent/'top100/tag-domains.json').read_text())
def group(domain,tags):
 for tag in tags.split():
  assert tag not in m,tag
  m[tag]=domain
# These two old broad mappings become specific groups in the expanded taxonomy.
# The expansion analysis applies this same map to both 1-100 and 1-200.
m['immunology']='Immunology';m['metabolomics']='Metabolomics'
group('Ecology & conservation','animal-detection bioacoustics biodiversity camera-traps conservation conservation-ai ecology megadetector wildlife-detection wildlife-monitoring')
group('Biomechanics & physiology','biomechanics musculoskeletal-models')
group('Immunology','antibody-design antibody-engineering nanobody-design')
group('Gene regulation','3d-genome chromatin contact-matrix cooler epigenetics epigenomics gene-regulation hi-c motif-discovery sequence-logo transcription-factors')
group('Genetic variation','genetics gwas coalescent genetic-maps hail hgvs maf-files msprime plink population-stratification population-structure population-study prs snp tree-sequences tskit')
group('Gene expression','deseq2 geo-database htseq kallisto microarray pseudoalignment rna-sequencing transcript')
group('Single-cell & spatial omics','cell-fate-transitions doublets scrna-seq-analysis')
group('Genome assembly & annotation','contigs download-genomes genbank genome-assembly-evaluation genometools genomic-intervals genomic-ranges gff3 lab-project-refgenie liftover medaka reference-genome synteny ucsc')
group('Sequence processing','amino-acid-sequence amino-acids fgbio genome-sequencing high-throughput-sequencing k-mers kmer nanopore ngs-analysis nucleotide-sequence nucleotides protein-sequence sequence-alignments')
group('Microbiome & metagenomics','ancom ancombc ancombc2 bacteria bacterial-genomes biobakery differential-abundance-analysis hitchip hitchip-atlas human-microbiome metagenomic-classification microbial-genomics microbiology microbiome-analysis phyloseq prophyle secom sourmash taxonomic-classification taxonomic-profiling')
group('Phylogenetics & evolution','phylogenetic-compression phylogeny')
group('Protein structure & biophysics','biophysics free-energy hh-suite hhblits hhpred hhsearch miniprotein-design peptide-design peptides pka-predictions profile-profile-search protein-engineering protein-structure-analysis')
group('Proteomics','peptide-spectrum-matches proteomics-data')
group('Cheminformatics & drug discovery','cdx cdxml chemical-reactions cml drugs e3fp mdl-molfile mol2 molecular-design molecular-indexes molecule-editor molecule-generation pharma pharmaceutical pharmaceuticals reaction-informatics')
group('Systems biology & ontologies','biolink biolink-model enrichment goslim-terms monarchinitiative ncats-translator obo-files obo-formatted-ontologies')
group('Biomedical text & clinical data','biomedical-informatics clinical-report clinical-trials medical-report-generate medical-report-generation pubmed pubmed-central')
group('Neuroscience & behavior','aperiodic-exponent bci-benchmarks bdf-toolbox beamformer computational-psychiatry computational-psychology dandi-archive electrophysiology fieldtrip fooof ieeg lfp local-field-potential mathematical-neuroscience nengo neural-computation neurophysiology seeg specparam spectral-parameterization')
group('Bioimaging','3d-slicer-extension aicsimageio brain-tumor-segmentation brats2021 breast-cancer-diagnosis chest-radiographs chest-xray chest-xray-images chest-xrays cxr cxr-images dcm dicom-files dicom-image dicom-image-viewer dicom-pr dicom-rt dicom-seg dicom-web-viewer dicomweb export-dicom fo-dicom image-metadata medical-image-classification medical-image-detection medical-image-reconstruction medical-image-registration medical-images mitk monai multiplanar-reconstruction ome-zarr ome-zarr-converter pacs torchxrayvision weasis')
group('Computing infrastructure','bioinformatics-pipeline crypt4gh ega ega-archive ga4gh gds-format lab-project-pephub nf-core scientific-workflows scipipe wdl workflow-description-language workflow-execution')
group('General biology & multi-omics','analyzing-genomic-data bioinformatics-algorithms genomics-data lifescience omics-data-integration')
(r/'tag-domains.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
print('Tag mappings',len(m))
