# Working classification vocabulary 0.5-working

Source-evidenced navigation categories, not an adopted ontology. Categories overlap. Rule assignments remain provisional. Repository and document subjects are distinct.

## Scientific field

| ID | Label | Definition |
| --- | --- | --- |
| `genomics-genetics` | Genomics and genetics | Genome organization, variation, inheritance and genotype-phenotype relationships; not every operation on sequence files. |
| `transcriptomics` | Transcriptomics | RNA abundance, expression, splicing and transcript-level analysis. |
| `epigenomics` | Epigenomics | Chromatin state, accessibility and DNA modification analyses. |
| `proteomics` | Proteomics | Protein abundance, identification and modification at proteome scale; coordinate analysis alone is structural biology. |
| `structural-biology` | Structural biology | Molecular structures, conformations and structural dynamics. |
| `metabolomics` | Metabolomics | Profiles and changes in metabolite measurements; network optimization alone does not establish metabolomics. |
| `systems-biology` | Systems biology | Mechanistic or network models of interacting biological components. |
| `microbiome` | Microbiome science | Microbial community composition, diversity and function. |
| `evolution` | Evolutionary biology | Evolutionary relationships, processes and selection; merely consuming a tree is insufficient. |
| `ecology` | Ecology | Organism-environment and community ecological questions; not automatically assigned to every microbiome tutorial. |
| `immunology` | Immunology | Immune populations, repertoires or function as an analytical subject; immune sample origin alone remains setting metadata. |
| `neuroscience` | Neuroscience | Neural signals, organization, activity and function. |
| `bioimage-analysis` | Bioimage analysis | Image-based biological detection, measurement and characterization; cell biology or ecology needs additional objective/interpretation evidence. |
| `cell-development` | Cell and developmental biology | Cellular organization, differentiation and developmental processes; single-cell resolution alone is insufficient. |
| `biochemistry` | Biochemistry | Molecular biochemical mechanisms not adequately described by another assigned field. |
| `pharmacology` | Pharmacology and toxicology | Drug action, dose response and toxicity. |
| `epidemiology` | Epidemiology | Population-level disease occurrence, exposures and risk. |
| `physiology` | Physiology and biomechanics | Organism or organ function and physical mechanics. |
| `biomedical-informatics` | Biomedical informatics | Clinical records, patient outcomes, biomedical text and structured biomedical knowledge as analytical subjects. A disease name, generic language model or clinical setting alone is insufficient. |
| `synthetic-biology` | Synthetic biology and biomolecular engineering | Design or engineering of biological sequences, molecules or systems for stated functional or structural objectives; natural-sequence analysis alone does not qualify. |

## Data modality

| ID | Label | Definition |
| --- | --- | --- |
| `airr` | Immune receptor sequencing | Adaptive immune receptor sequences and derived clonotypes. |
| `methylation-array` | DNA methylation array | Probe-level DNA methylation array measurements. |
| `rgb-image` | RGB organism or habitat images | Visible-light organism or habitat images; not automatically microscopy or ecological inference. |
| `scrna` | Single-cell RNA-seq | Cell-resolved RNA sequencing measurements or derived expression matrices. |
| `bulk-rna` | Bulk RNA-seq | Bulk RNA sequencing measurements or derived expression matrices. |
| `dna-variants` | Genotypes and sequence variants | Variant/genotype observations; do not infer sequencing versus array assay when unspecified. |
| `metabolite-profile` | Metabolite profiles | Metabolite measurements; do not infer mass spectrometry versus NMR from a table alone. |
| `growth` | Growth measurements | Growth or optical-density measurements. |
| `structure` | Molecular coordinates | Atomic coordinates; experimental or predicted origin is separate metadata. |
| `trajectory` | Molecular trajectories | Time-indexed molecular coordinates; analysis does not imply running the simulation. |
| `flow-cytometry` | Flow cytometry | Optical cytometry marker measurements. |
| `mass-cytometry` | Mass cytometry | Metal-tag cytometry measurements; not inferred solely from tool compatibility. |
| `microscopy` | Microscopy | Biological microscopy images, with optional optical subtype. |
| `community-profile` | Microbial community profiles | Taxon abundance and diversity data; amplicon versus shotgun assay may be unspecified. |
| `electrophysiology` | Electrophysiology | Electrical neural recordings or derived spike/unit tables. |
| `atac` | ATAC-seq | Chromatin accessibility sequencing. |
| `chip` | ChIP-seq | Chromatin immunoprecipitation sequencing. |
| `mass-spectrometry` | Mass spectrometry | Mass-spectral measurements; analyte type described separately. |
| `spatial-expression` | Spatial expression profiling | Expression observations with spatial registration; retain assay subtype if known. |
| `sequences` | Biological sequences | Nucleotide or amino-acid sequences; record molecule subtype and source when known. |
| `ancestral-trees` | Ancestral trees and tree sequences | Ancestral relationships along genomes, including simulated genealogies. |
| `model-data` | Model specifications and parameters | Equations, reaction schemes, parameters or initial conditions; a model input, not an experimental assay. |
| `motion-force` | Motion capture and forces | Body-marker trajectories and force measurements for biomechanical inference. |
| `chemical-assay` | Molecular structures and bioassay outcomes | Chemical representations paired with activity outcomes; do not infer clinical efficacy. |
| `community-vegetation` | Community species and environment tables | Species/community observations with environmental covariates. |
| `protein-profile` | Protein abundance profiles | Derived protein measurements; underlying assay must be separately evidenced. |
| `medical-imaging` | Medical imaging | Clinical or preclinical volumetric/radiological images such as MRI and CT; keep microscopy separate. |
| `clinical-records` | Clinical records and outcomes | Patient characteristics, treatment, follow-up and health outcomes. |
| `chemical-structures` | Chemical structures | Small-molecule representations such as SMILES, SDF or molecular graphs without assuming paired activity measurements. |
| `biomedical-text` | Biomedical text | Biomedical questions, literature or clinical narratives used as textual inputs. Record whether text is authored, observed or generated. |
| `biomedical-knowledge` | Biological relationships and knowledge graphs | Structured biological entities and relationships, including curated knowledge graphs and interaction networks; record whether relationships are measured, curated or inferred. |

## Analytical operation

| ID | Label | Definition |
| --- | --- | --- |
| `data-access` | Data access | Retrieve or stream supplied data; retrieval alone does not establish biological inference. |
| `phenotyping` | Image phenotyping | Extract organism/object shape or color measurements from images. |
| `data-preparation` | Data preparation | Import, subset, transform and reconcile data identities or representations. |
| `qc` | Quality assessment and filtering | Compute or inspect quality evidence and optionally filter; record whether metrics are supplied. |
| `normalization` | Normalization and scaling | Adjust measurements for scale or technical effects. |
| `feature-selection` | Feature selection | Select features by a stated criterion. |
| `dimension-reduction` | Dimensionality reduction | Compute embeddings or lower-dimensional projections. |
| `clustering` | Clustering | Infer groups from data; supplied group labels are not sufficient. |
| `marker-testing` | Marker testing | Compare expression across populations for marker evidence; distinct from replicated treatment inference. |
| `association` | Association testing | Test genotype-phenotype or other stated associations. |
| `group-comparison` | Group comparison | Compute group differences or tests; record data provenance and method. |
| `annotation` | Biological annotation | Assign biological labels or identities using stated evidence. |
| `structural-comparison` | Structural comparison | Align structures or measure coordinate differences such as RMSD. |
| `geometry` | Structural geometry | Compute molecular angles, contacts or other geometric descriptors. |
| `segmentation` | Image segmentation | Partition image content into objects or regions. |
| `diversity` | Diversity estimation | Compute diversity measures for a specified target, such as communities or immune repertoires. |
| `descriptive-analysis` | Descriptive analysis and visualization | Summarize or visualize biological observations; not automatically inferential statistics. |
| `simulation` | Simulation or mechanistic modeling | Run a mechanistic or stochastic model to generate outcomes; model construction and supplied simulations are separate. |
| `prediction` | Predictive modeling | Fit or apply a predictive model; consuming predictions alone is insufficient. |
| `integration` | Data integration | Combine datasets/modalities or correct cross-dataset effects. |
| `alignment` | Sequence alignment | Compute sequence/read alignments; supplied alignments alone are insufficient. |
| `quantification` | Quantification | Estimate abundances or feature measurements from lower-level observations. |
| `enrichment` | Enrichment analysis | Test or score sets/pathways against an explicit background or ranking. |
| `model-construction` | Mechanistic model construction | Define reactions, equations, parameters or constraints; distinguish specification from running simulations. |
| `inverse-modeling` | Inverse modeling | Infer physical states, forces or parameters from observations with a forward model. |
| `statistical-modeling` | Statistical model fitting | Fit a statistical model for a stated inferential target; fitting alone does not establish predictive validation. |
| `spatial-statistics` | Spatial statistics | Compute spatial organization, autocorrelation or neighborhood statistics; not gene-set enrichment. |
| `feature-extraction` | Feature and representation extraction | Compute descriptors or vector representations from inputs, including radiomics and pretrained embeddings; distinct from selecting existing features or training the underlying model. |
| `sequence-design` | Sequence and probe design | Design nucleotide or amino-acid sequences, primers or hybridization probes for stated objectives; not sequence alignment or identification. |
| `sequence-search` | Sequence database search | Search sequence collections with sequence queries or profile models; distinguish search from building an alignment. |
