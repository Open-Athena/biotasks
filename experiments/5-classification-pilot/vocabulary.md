# Draft classification vocabulary 0.3-working

This is a working navigation vocabulary, not an adopted ontology. Terms overlap. Exercised means at least one pilot assignment, not independent validation. See [working rules](decisions.md) for field/setting boundaries and operation roles.

Use scientific field for browsing, data modality for observations/inputs, and operation for analytical work. Keep file format, input origin, assay subtype, design and biological setting separate. An assignment needs subject/revision, evidence, rationale and review status. Operation assignments also need a role and target. No automatic repository-to-notebook inheritance.

Review states for a facet are unreviewed, content-supported, insufficient evidence, not applicable or disputed. Label-level states can be suggested, content-supported, needs-review or rejected. Do not force a biological field onto a generic utility. None of these states claims executable validation.

## Scientific field

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
| `genomics-genetics` | Genomics and genetics | Genome organization, variation, inheritance and genotype-phenotype relationships; not every operation on sequence files. | Exercised |
| `transcriptomics` | Transcriptomics | RNA abundance, expression, splicing and transcript-level analysis. | Exercised |
| `epigenomics` | Epigenomics | Chromatin state, accessibility and DNA modification analyses. | Exercised |
| `proteomics` | Proteomics | Protein abundance, identification and modification at proteome scale; coordinate analysis alone is structural biology. | Exercised |
| `structural-biology` | Structural biology | Molecular structures, conformations and structural dynamics. | Exercised |
| `metabolomics` | Metabolomics | Profiles and changes in metabolite measurements; network optimization alone does not establish metabolomics. | Exercised |
| `systems-biology` | Systems biology | Mechanistic or network models of interacting biological components. | Exercised |
| `microbiome` | Microbiome science | Microbial community composition, diversity and function. | Exercised |
| `evolution` | Evolutionary biology | Evolutionary relationships, processes and selection; merely consuming a tree is insufficient. | Exercised |
| `ecology` | Ecology | Organism-environment and community ecological questions; not automatically assigned to every microbiome tutorial. | Exercised |
| `immunology` | Immunology | Immune populations, repertoires or function as an analytical subject; immune sample origin alone remains setting metadata. | Exercised |
| `neuroscience` | Neuroscience | Neural signals, organization, activity and function. | Exercised |
| `bioimage-analysis` | Bioimage analysis | Image-based biological detection, measurement and characterization; cell biology or ecology needs additional objective/interpretation evidence. | Exercised |
| `cell-development` | Cell and developmental biology | Cellular organization, differentiation and developmental processes; single-cell resolution alone is insufficient. | Exercised |
| `biochemistry` | Biochemistry | Molecular biochemical mechanisms not adequately described by another assigned field. | Exercised |
| `pharmacology` | Pharmacology and toxicology | Drug action, dose response and toxicity. | Exercised |
| `epidemiology` | Epidemiology | Population-level disease occurrence, exposures and risk. | Exercised |
| `physiology` | Physiology and biomechanics | Organism or organ function and physical mechanics. | Exercised |

## Data modality

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
| `airr` | Immune receptor sequencing | Adaptive immune receptor sequences and derived clonotypes. | Exercised |
| `methylation-array` | DNA methylation array | Probe-level DNA methylation array measurements. | Exercised |
| `rgb-image` | RGB organism or habitat images | Visible-light organism or habitat images; not automatically microscopy or ecological inference. | Exercised |
| `scrna` | Single-cell RNA-seq | Cell-resolved RNA sequencing measurements or derived expression matrices. | Exercised |
| `bulk-rna` | Bulk RNA-seq | Bulk RNA sequencing measurements or derived expression matrices. | Exercised |
| `dna-variants` | Genotypes and sequence variants | Variant/genotype observations; do not infer sequencing versus array assay when unspecified. | Exercised |
| `metabolite-profile` | Metabolite profiles | Metabolite measurements; do not infer mass spectrometry versus NMR from a table alone. | Exercised |
| `growth` | Growth measurements | Growth or optical-density measurements. | Exercised |
| `structure` | Molecular coordinates | Atomic coordinates; experimental or predicted origin is separate metadata. | Exercised |
| `trajectory` | Molecular trajectories | Time-indexed molecular coordinates; analysis does not imply running the simulation. | Exercised |
| `flow-cytometry` | Flow cytometry | Optical cytometry marker measurements. | Exercised |
| `mass-cytometry` | Mass cytometry | Metal-tag cytometry measurements; not inferred solely from tool compatibility. | Exercised |
| `microscopy` | Microscopy | Biological microscopy images, with optional optical subtype. | Exercised |
| `community-profile` | Microbial community profiles | Taxon abundance and diversity data; amplicon versus shotgun assay may be unspecified. | Exercised |
| `electrophysiology` | Electrophysiology | Electrical neural recordings or derived spike/unit tables. | Exercised |
| `atac` | ATAC-seq | Chromatin accessibility sequencing. | Exercised |
| `chip` | ChIP-seq | Chromatin immunoprecipitation sequencing. | Exercised |
| `mass-spectrometry` | Mass spectrometry | Mass-spectral measurements; analyte type described separately. | Exercised |
| `spatial-expression` | Spatial expression profiling | Expression observations with spatial registration; retain assay subtype if known. | Exercised |
| `sequences` | Biological sequences | Nucleotide or amino-acid sequences; record molecule subtype and source when known. | Exercised |
| `ancestral-trees` | Ancestral trees and tree sequences | Ancestral relationships along genomes, including simulated genealogies. | Exercised |
| `model-data` | Model specifications and parameters | Equations, reaction schemes, parameters or initial conditions; a model input, not an experimental assay. | Exercised |
| `motion-force` | Motion capture and forces | Body-marker trajectories and force measurements for biomechanical inference. | Exercised |
| `chemical-assay` | Molecular structures and bioassay outcomes | Chemical representations paired with activity outcomes; do not infer clinical efficacy. | Exercised |
| `community-vegetation` | Community species and environment tables | Species/community observations with environmental covariates. | Exercised |
| `protein-profile` | Protein abundance profiles | Derived protein measurements; underlying assay must be separately evidenced. | Exercised |

## Analytical operation

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
| `data-access` | Data access | Retrieve or stream supplied data; retrieval alone does not establish biological inference. | Exercised |
| `phenotyping` | Image phenotyping | Extract organism/object shape or color measurements from images. | Exercised |
| `data-preparation` | Data preparation | Import, subset, transform and reconcile data identities or representations. | Exercised |
| `qc` | Quality assessment and filtering | Compute or inspect quality evidence and optionally filter; record whether metrics are supplied. | Exercised |
| `normalization` | Normalization and scaling | Adjust measurements for scale or technical effects. | Exercised |
| `feature-selection` | Feature selection | Select features by a stated criterion. | Exercised |
| `dimension-reduction` | Dimensionality reduction | Compute embeddings or lower-dimensional projections. | Exercised |
| `clustering` | Clustering | Infer groups from data; supplied group labels are not sufficient. | Exercised |
| `marker-testing` | Marker testing | Compare expression across populations for marker evidence; distinct from replicated treatment inference. | Exercised |
| `association` | Association testing | Test genotype-phenotype or other stated associations. | Exercised |
| `group-comparison` | Group comparison | Compute group differences or tests; record data provenance and method. | Exercised |
| `annotation` | Biological annotation | Assign biological labels or identities using stated evidence. | Exercised |
| `structural-comparison` | Structural comparison | Align structures or measure coordinate differences such as RMSD. | Exercised |
| `geometry` | Structural geometry | Compute molecular angles, contacts or other geometric descriptors. | Exercised |
| `segmentation` | Image segmentation | Partition image content into objects or regions. | Exercised |
| `diversity` | Diversity estimation | Compute diversity measures for a specified target, such as communities or immune repertoires. | Exercised |
| `descriptive-analysis` | Descriptive analysis and visualization | Summarize or visualize biological observations; not automatically inferential statistics. | Exercised |
| `simulation` | Simulation or mechanistic modeling | Run a mechanistic or stochastic model to generate outcomes; model construction and supplied simulations are separate. | Exercised |
| `prediction` | Predictive modeling | Fit or apply a predictive model; consuming predictions alone is insufficient. | Exercised |
| `integration` | Data integration | Combine datasets/modalities or correct cross-dataset effects. | Exercised |
| `alignment` | Sequence alignment | Compute sequence/read alignments; supplied alignments alone are insufficient. | Exercised |
| `quantification` | Quantification | Estimate abundances or feature measurements from lower-level observations. | Exercised |
| `enrichment` | Enrichment analysis | Test or score sets/pathways against an explicit background or ranking. | Exercised |
| `model-construction` | Mechanistic model construction | Define reactions, equations, parameters or constraints; distinguish specification from running simulations. | Exercised |
| `inverse-modeling` | Inverse modeling | Infer physical states, forces or parameters from observations with a forward model. | Exercised |
| `statistical-modeling` | Statistical model fitting | Fit a statistical model for a stated inferential target; fitting alone does not establish predictive validation. | Exercised |
| `spatial-statistics` | Spatial statistics | Compute spatial organization, autocorrelation or neighborhood statistics; not gene-set enrichment. | Exercised |
