"""Explicit assistant annotations for newly selected sources; preserve the baseline."""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent / "baseline/data/top200-2026-09-29"
data = json.loads((HERE / "provisional.json").read_text())
sources = {s["source_id"]: s for s in data["sources"]}
with (BASE / "source-annotations-2026-09-29.csv").open() as f:
    baseline = {r["source_id"]: r for r in csv.DictReader(f)}
a = dict(baseline)
short = {}
for key in sources.keys() - baseline.keys():
    name = key.rsplit("/", 1)[-1].split(":")[-1]
    if name == "cellchat":
        name = key[7:]
    assert name not in short, (name, key)
    short[name] = key


def group(domain, topic, names):
    for name in names.split():
        key = short[name]
        assert key not in a, key
        a[key] = dict(
            source_id=key,
            source_type="Software",
            primary_domain=domain,
            manual_topic=topic,
            scope_note="",
            evidence_urls=";".join(sources[key]["evidence_urls"]),
        )


group(
    "Sequence processing", "Read and sequence alignment", "bwa-mem2 ngmlr segemehl-0.3.4.tar.gz kma"
)
group(
    "Sequence processing",
    "Sequence similarity and alignment",
    "prank-msa pasta tcoffee sequence_align cdhit poav2.tar.gz",
)
group(
    "Sequence processing",
    "Read processing and quality control",
    "samblaster mosdepth umi-tools yacrd trimadap nanoplot qualimap pandaseq",
)
group(
    "Sequence processing",
    "Alignment files and sequencing formats",
    "samsift ngs fast5 pod5-file-format escapepod-rs nanoget interop noodles screed",
)
group("Sequence processing", "Nanopore basecalling", "dorado")
group("Sequence processing", "Sequence manipulation", "khmer seguid-python barcode")
group(
    "Genome assembly & annotation",
    "Gene prediction and genome annotation",
    "barrnap transdecoder glimmerhmm-3.0.4.tar.gz aragorn1.2.41.c eggnog-mapper bakta org.hs.eg.db",
)
group("Genome assembly & annotation", "Genome assembly", "racon flye hifiasm bandage")
group(
    "Genome assembly & annotation",
    "Genomic intervals and coordinates",
    "bedops plyranges annotatr py2bit deeptools_intervals liftover crossmap",
)
group(
    "Genome assembly & annotation",
    "Genome track visualization",
    "jbrowse-components igv igv.js karyoploter gggenomes dnafeaturesviewer circos-0.69-9.tgz trackviewer",
)
group(
    "Genetic variation",
    "Variant formats and annotation",
    "vt vcfpy vcflib pyvcf myvariant.py vrs-python eva-sub-cli seqarray bgen libplinkio",
)
group("Genetic variation", "Variant calling and phasing", "whatshap sniffles")
group("Genetic variation", "Copy-number analysis", "cnvkit fastseg")
group("Genetic variation", "Association and population genetics", "gwastools")
group("Genetic variation", "Ancestry and population simulation", "fwdpy11 moments libsequence")
group("Gene expression", "Expression quantification and transcript assembly", "rsem")
group("Gene expression", "Transcript and splicing analysis", "portcullis altanalyze")
group("Gene expression", "Bulk differential expression", "ballgown pydeseq2 derfinder")
group("Gene expression", "Microarray processing and normalization", "affyplm gcrma lumi beadarray")
group("Gene expression", "Expression normalization and variation", "ruvseq")
group("Gene expression", "Expression visualization", "glimmav2")
group("Gene expression", "Expression data access", "recount3")
group("Single-cell & spatial omics", "Single-cell preprocessing", "scds scprep")
group(
    "Single-cell & spatial omics",
    "Single-cell analysis and annotation",
    "celltypist celda muscat milor nebulosa dittoseq cellbrowser cellxgene scp scimap sure scanpy-scripts",
)
group(
    "Single-cell & spatial omics",
    "Single-cell analysis resources",
    "scrna-seq_notes awesome-deep-learning-single-cell-papers",
)
group("Single-cell & spatial omics", "Single-cell containers and storage", "alabaster.sce anndatar")
group(
    "Single-cell & spatial omics",
    "Single-cell integration and representation",
    "scib cell2sentence muon zinbwave",
)
group(
    "Single-cell & spatial omics",
    "Single-cell perturbation analysis",
    "pdex-0.3.0.tar.gz cell_eval2-0.16.0.tar.gz",
)
group(
    "Single-cell & spatial omics",
    "Cell trajectories and differentiation",
    "scvelo velocyto.py tradeseq destiny",
)
group(
    "Single-cell & spatial omics",
    "Cell-cell communication",
    "liana jinworks/cellchat sqjin/cellchat",
)
group("Single-cell & spatial omics", "Spatial expression analysis", "taggd")
group(
    "Gene regulation",
    "Sequence motifs and visualization",
    "rcistarget universalmotif motifdb motifstack seqpattern",
)
group(
    "Gene regulation",
    "Chromatin signal processing",
    "chromvar diffbind chipseq chippeakanno greylistchip bamsignals macs signac fp-tools enrichedheatmap genomation",
)
group(
    "Gene regulation",
    "DNA methylation",
    "champ dmrcate dss missmethyl watermelon methylkit f5c sesame epidish",
)
group("Gene regulation", "Chromosome conformation", "hicexplorer pairix")
group("Gene regulation", "Regulatory network inference", "genie3 viper")
group("General biology & multi-omics", "Genomic foundation models", "hyena-dna")
group(
    "General biology & multi-omics",
    "General biological analysis libraries",
    "emboss_6.6.0_src_all.tar.gz biopytools",
)
group("General biology & multi-omics", "Multi-omics integration", "mofa2 mfuzz")
group(
    "General biology & multi-omics",
    "Biological database access",
    "intermine-ws-python biomart bioservices genomicdatacommons tcgautils",
)
group(
    "General biology & multi-omics",
    "Biological teaching and discovery resources",
    "awesome bds-files",
)
group(
    "General biology & multi-omics",
    "Flow cytometry analysis",
    "flowclust flowsom flowviz opencyto flowstats ggcyto flowutils",
)
group("General biology & multi-omics", "Flow cytometry formats", "ncdfflow cytoml")
group("General biology & multi-omics", "Synthetic biology and cloning", "poly pydna cello")
group("General biology & multi-omics", "Laboratory automation", "opentrons")
group(
    "Microbiome & metagenomics",
    "Community profiling and diversity",
    "abundancebin_1.0.1_src_all.tar.gz mothur aldex_bioc maaslin2 itsxpress gtdbtk",
)
group("Microbiome & metagenomics", "Microbial typing and pathogen detection", "rgi amr bactopia")
group("Phylogenetics & evolution", "Phylogenetic orthology inference", "orthofinder proteinortho")
group("Phylogenetics & evolution", "Pathogen evolution and surveillance", "usher nextclade gofasta")
group("Phylogenetics & evolution", "Comparative phylogenetic data", "commonnexus ipyrad")
group("RNA structure", "RNA interaction prediction", "intarna")
group("Proteomics", "Mass spectrometry analysis", "msstats")
group("Proteomics", "Mass spectrometry interfaces", "msexperiment")
group("Proteomics", "Protein localization analysis", "proloc")
group("Proteomics", "Protein database access", "uniprot.ws")
group(
    "Protein structure & biophysics",
    "Protein homology and domain annotation",
    "bio-searchio-hmmer-1.7.3.tar.gz",
)
group(
    "Protein structure & biophysics",
    "Protein models and design",
    "openfold-3 open-af3 bioemu chroma evodiff progen promb masif",
)
group(
    "Protein structure & biophysics",
    "Molecular structures and visualization",
    "ngl mol-view-spec hbat ccp4i2",
)
group(
    "Protein structure & biophysics",
    "Molecular simulation and trajectory analysis",
    "chemfiles.py torchmd openmmforcefields atomworks",
)
group("Protein structure & biophysics", "Structure modeling evaluation and data", "dynamicpdb tape")
group(
    "Protein structure & biophysics",
    "Protein modeling resources",
    "awesome-protein-representation-learning dl4proteins-notebooks",
)
group(
    "Protein structure & biophysics", "Biomolecular model computation", "colabfold-legacy-kernels"
)
group("Immunology", "Immune receptor annotation", "arda vdjtools screpertoire abnumber")
group("Immunology", "Antigen presentation and vaccine peptides", "mhcflurry")
group("Immunology", "Tumor immune deconvolution", "quantiseqr")
group("Metabolomics", "Mass spectra and chemical composition", "rainbow isospec rdisop msentropy")
group("Ecology & conservation", "Biodiversity data access", "pygbif pyobis")
group("Ecology & conservation", "Ecological image analysis", "deepforest")
group("Cheminformatics & drug discovery", "Cheminformatics resources", "awesome-cheminformatics")
group(
    "Cheminformatics & drug discovery",
    "Molecular representations and descriptors",
    "pmapper mordred mols2grid",
)
group("Cheminformatics & drug discovery", "Molecular modeling and visualization", "avogadrolibs")
group(
    "Cheminformatics & drug discovery",
    "Molecular property and interaction prediction",
    "admet_ai dgl-lifesci chemicalx chainer-chemistry unimol_tools",
)
group(
    "Cheminformatics & drug discovery",
    "Molecular design and generation",
    "reinvent4 openchem bionemo-recipes",
)
group("Cheminformatics & drug discovery", "Cheminformatics analysis", "chemminer plip")
group(
    "Systems biology & ontologies",
    "Pathway and gene-set analysis",
    "category gostats goseq gage geneoverlap simplifyenrichment rgreat globalancova safe spia",
)
group("Systems biology & ontologies", "Biological identifiers and ontologies", "go.db simona")
group("Systems biology & ontologies", "Biological networks and metabolism", "omnipathr minet rcy3")
group("Systems biology & ontologies", "Biological activity inference", "progeny")
group("Systems biology & ontologies", "Biochemical reaction and diffusion simulation", "basico")
group("Bioimaging", "Image processing and viewing", "tiffslide slideio ami mitk invesalius3")
group(
    "Bioimaging",
    "Medical image segmentation",
    "medsam2 vm-unet medical-transformer vnet.pytorch lungmask min_max_similarity",
)
group(
    "Bioimaging",
    "Medical image representations",
    "modelsgenesis generativemodels retfound medclip biomedparse biomedgpt",
)
group(
    "Bioimaging", "Biological and medical image analysis", "medicaltorch btrack plantcv micro-sam"
)
group("Bioimaging", "Optical tomography", "sax-nerf")
group("Bioimaging", "Image metadata and plugins", "nd2reader napari-omero useq-schema")
group(
    "Neuroscience & behavior", "Neuroimaging", "freesurfer dipy fmriprep niworkflows nitransforms"
)
group(
    "Neuroscience & behavior",
    "Neural recording and signal analysis",
    "spikeinterface nitime efel pyabf",
)
group("Neuroscience & behavior", "Neural simulation", "brainpy leabra mdf")
group(
    "Neuroscience & behavior",
    "Neuroanatomy and connectomics",
    "brainrender morphio skeletor cloud-volume webknossos-libs",
)
group("Neuroscience & behavior", "Neural data access", "openneuro-py")
group(
    "Neuroscience & behavior",
    "Neuroscience teaching and resources",
    "open-computational-neuroscience-resources",
)
group(
    "Biomedical text & clinical data",
    "Biomedical language processing",
    "cblue biobert-pretrained chemdataextractor",
)
group("Biomedical text & clinical data", "Biomedical knowledge graphs", "primekg tablassert")
group(
    "Biomedical text & clinical data",
    "Medical data access and representation",
    "meds osteosarc delphi-epidata",
)
group("Biomedical text & clinical data", "Survival analysis", "survcomp")
group(
    "Computing infrastructure",
    "Bioinformatics workflow platforms",
    "arvados galaxy-lib miniwdl latch sevenbridges-python wdl systempiper snakemake-interface-scheduler-plugins pybiolib-1.4.551.tar.gz datajoint-python pydra",
)
group(
    "Computing infrastructure",
    "Parallel computing and package infrastructure",
    "containers rigraphlib lpsymphony seq biocutils",
)
group(
    "Computing infrastructure",
    "Scientific storage and I/O",
    "raggedexperiment biocframe nucleus genomicfiles",
)
group(
    "Computing infrastructure",
    "Statistics and visualization for biology",
    "dyndoc reportingtools mlinterfaces pcatools ihw roc",
)


group("Gene regulation", "MicroRNA target analysis", "microrna")


def types(kind, names):
    for name in names.split():
        a[short[name]]["source_type"] = kind


types(
    "Infrastructure",
    "alabaster.sce anndatar ncdfflow cytoml msexperiment meds mdf morphio cloud-volume webknossos-libs useq-schema niworkflows nitransforms colabfold-legacy-kernels arvados galaxy-lib miniwdl latch sevenbridges-python wdl systempiper snakemake-interface-scheduler-plugins pybiolib-1.4.551.tar.gz datajoint-python pydra containers rigraphlib lpsymphony seq biocutils raggedexperiment biocframe nucleus genomicfiles dyndoc reportingtools mlinterfaces",
)
types("Workflow", "bactopia fmriprep scanpy-scripts scp")
types(
    "Research implementation",
    "hyena-dna cell2sentence sure openfold-3 open-af3 bioemu chroma evodiff progen masif medsam2 vm-unet medical-transformer vnet.pytorch min_max_similarity modelsgenesis retfound medclip biomedparse biomedgpt sax-nerf",
)
types(
    "Resource index",
    "scrna-seq_notes awesome-deep-learning-single-cell-papers awesome awesome-protein-representation-learning awesome-cheminformatics open-computational-neuroscience-resources",
)
types("Tutorial/course", "bds-files dl4proteins-notebooks")
types("Data resource", "go.db org.hs.eg.db motifdb dynamicpdb primekg osteosarc")

notes = {
    "leabra": "Explicit cognitive-neuroscience framework and biological neuron modeling; retained separately from general neuromorphic training frameworks.",
    "mdf": "Cross-framework modeling specification with explicit computational-neuroscience and cognitive-science scope; also supports general ML.",
    "datajoint-python": "General scientific workflow infrastructure with documented neuroscience Elements pipelines; broad ecosystem-support inclusion.",
    "rigraphlib": "Generic graph library retained as dedicated Bioconductor/libscran ecosystem support; not a distinct biological analysis field.",
    "lpsymphony": "Generic integer-programming solver in Bioconductor; retained as ecosystem support, not a distinct biological analysis field.",
    "sequence_align": "General sequence-alignment implementation selected by the biological package screen. Biological sequence applicability is broader than a dedicated biological workflow; borderline inclusion.",
    "sax-nerf": "Mixed anatomical and object CT reconstruction. Whole-repository stars include nonbiological applications.",
    "colabfold-legacy-kernels": "Independent native CUDA implementations supporting ColabFold on older GPU architectures; infrastructure, not a second protein-model method.",
    "cell_eval2-0.16.0.tar.gz": "Official PyPI source distribution; package describes itself as a reimplementation of cell-eval. This identity and label do not establish verified evaluation equivalence.",
    "deepforest": "Ecological imagery of tree crowns and birds; primary group is ecology rather than the cross-cutting bioimaging group.",
    "plantcv": "Image-based plant phenotyping; primary group is bioimaging. Primary labels cannot describe all cross-cutting applications.",
    "open-af3": "Independent research implementation claiming AlphaFold3 architecture; no execution or scientific equivalence was validated.",
    "jinworks/cellchat": "Maintained CellChat repository. The older sqjin/CellChat source also remains in the recorded pool. Distinct repository identities are retained under the baseline policy, so this is not a count of independent scientific methods.",
    "sqjin/cellchat": "Older CellChat source, distinct repository identity from jinworks/CellChat. Shared lineage means source diversity overstates independent method diversity.",
    "emboss_6.6.0_src_all.tar.gz": "Versioned Galaxy source mirror; official FTP source named in the pinned recipe. Mirror returned HTTP 200 to HEAD; archive contents were not downloaded or checksum-compared.",
    "rainbow": "Cross-domain chromatography and mass-spectrometry formats; assigned metabolomics, also applicable to proteomics and analytical chemistry.",
    "isospec": "Cross-domain isotopic-distribution calculator; assigned metabolomics alongside mass-spectrum composition tools.",
    "chemdataextractor": "Chemical literature extraction; primary biomedical-text group captures the activity, not exclusively biomedical scope.",
    "avogadrolibs": "Cross-domain molecular visualization with explicit molecular modeling and bioinformatics scope; also supports materials science.",
    "biopytools": "README describes a broad bioinformatics toolkit; repository description is blank. No candidate execution was performed.",
}
for name, note in notes.items():
    a[short[name]]["scope_note"] = note
missing = sources.keys() - a.keys()
assert not missing, sorted(missing)
assert all(a[k] == v for k, v in baseline.items())
with (HERE / "source-annotations.csv").open("w") as f:
    w = csv.DictWriter(f, fieldnames=next(iter(baseline.values())).keys())
    w.writeheader()
    w.writerows(a[k] for k in sorted(a))
print(f"Annotated {len(a)} sources, {len(a) - len(baseline)} additions; baseline unchanged.")
