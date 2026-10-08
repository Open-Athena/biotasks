# Draft classification vocabulary v0.1

This is a local proposal, not an adopted ontology. Terms can overlap. A term exercised in the pilot has at least one source-backed assignment, not independent validation. An empty assignment must have a reason: not inspected, insufficient evidence, not applicable, or disputed. General-purpose infrastructure should not be forced into a biological field.

Use scientific field for browsing; modality describes observations/inputs; operation describes analytical work. Biological question, experimental design and setting remain optional evidence-backed metadata. Keep notebook file format separate from biological modality. Record technical origin (observed, adapted, simulated, predicted, mixed or unknown) separately from experimental design.

Every assignment needs a stable term ID, subject ID/revision, status, evidence location, rationale and reviewer. Operations additionally need a role: implemented, exercise, discussed-only or upstream-supplied. “Implemented” means source code is present, not executed or verified. If code is disabled or incomplete, state that limitation. Multiple labels are allowed, never inherited silently.

## Scientific field

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
| `genomics-genetics` | Genomics and genetics | Genome organization, variation, inheritance and genotype-phenotype relationships; not every operation on sequence files. | Exercised |
| `transcriptomics` | Transcriptomics | RNA abundance, expression, splicing and transcript-level analysis. | Exercised |
| `epigenomics` | Epigenomics | Chromatin state, accessibility and DNA modification analyses. | Untested proposal |
| `proteomics` | Proteomics | Protein abundance, identification and modification at proteome scale; coordinate analysis alone is structural biology. | Untested proposal |
| `structural-biology` | Structural biology | Molecular structures, conformations and structural dynamics. | Exercised |
| `metabolomics` | Metabolomics | Profiles and changes in metabolite measurements; network optimization alone does not establish metabolomics. | Exercised |
| `systems-biology` | Systems biology | Mechanistic or network models of interacting biological components. | Exercised |
| `microbiome` | Microbiome science | Microbial community composition, diversity and function. | Exercised |
| `evolution` | Evolutionary biology | Evolutionary relationships, processes and selection; merely consuming a tree is insufficient. | Untested proposal |
| `ecology` | Ecology | Organism-environment and community ecological questions; not automatically assigned to every microbiome tutorial. | Untested proposal |
| `immunology` | Immunology | Immune populations, repertoires and immune function; immune sample origin alone can remain setting metadata. | Exercised |
| `neuroscience` | Neuroscience | Neural signals, organization, activity and function. | Exercised |
| `bioimage-analysis` | Bioimage analysis | Biological image-based measurement and characterization. Boundary with cell biology remains under review. | Exercised |
| `cell-development` | Cell and developmental biology | Cellular organization, differentiation and developmental processes; single-cell resolution alone is insufficient. | Untested proposal |
| `biochemistry` | Biochemistry | Molecular biochemical mechanisms not adequately described by another assigned field. | Untested proposal |
| `pharmacology` | Pharmacology and toxicology | Drug action, dose response and toxicity. | Untested proposal |
| `epidemiology` | Epidemiology | Population-level disease occurrence, exposures and risk. | Untested proposal |
| `physiology` | Physiology and biomechanics | Organism or organ function and physical mechanics. | Untested proposal |

## Data modality

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
| `scrna` | Single-cell RNA-seq | Cell-resolved RNA sequencing measurements or derived expression matrices. | Exercised |
| `bulk-rna` | Bulk RNA-seq | Bulk RNA sequencing measurements or derived expression matrices. | Untested proposal |
| `dna-variants` | Genotypes and sequence variants | Variant/genotype observations; do not infer sequencing versus array assay when unspecified. | Exercised |
| `metabolite-profile` | Metabolite profiles | Metabolite measurements; do not infer mass spectrometry versus NMR from a table alone. | Exercised |
| `growth` | Growth measurements | Growth or optical-density measurements. | Exercised |
| `structure` | Molecular coordinates | Atomic coordinates; experimental or predicted origin is separate metadata. | Exercised |
| `trajectory` | Molecular trajectories | Time-indexed molecular coordinates; analysis does not imply running the simulation. | Exercised |
| `flow-cytometry` | Flow cytometry | Optical cytometry marker measurements. | Exercised |
| `mass-cytometry` | Mass cytometry | Metal-tag cytometry measurements; not inferred solely from tool compatibility. | Untested proposal |
| `microscopy` | Microscopy | Biological microscopy images, with optional optical subtype. | Exercised |
| `community-profile` | Microbial community profiles | Taxon abundance and diversity data; amplicon versus shotgun assay may be unspecified. | Exercised |
| `electrophysiology` | Electrophysiology | Electrical neural recordings or derived spike/unit tables. | Exercised |
| `atac` | ATAC-seq | Chromatin accessibility sequencing. | Untested proposal |
| `chip` | ChIP-seq | Chromatin immunoprecipitation sequencing. | Untested proposal |
| `mass-spectrometry` | Mass spectrometry | Mass-spectral measurements; analyte type described separately. | Untested proposal |
| `spatial-expression` | Spatial expression profiling | Expression observations with spatial registration; retain assay subtype if known. | Untested proposal |

## Analytical operation

| ID | Label | Definition | Pilot |
| --- | --- | --- | --- |
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
| `diversity` | Diversity estimation | Compute community richness, evenness or related diversity measures. | Exercised |
| `descriptive-analysis` | Descriptive analysis and visualization | Summarize or visualize biological observations; not automatically inferential statistics. | Exercised |
| `simulation` | Simulation or mechanistic modeling | Generate model outcomes; supplied simulated data do not establish this operation. | Exercised |
| `prediction` | Predictive modeling | Fit or apply a predictive model; consuming predictions alone is insufficient. | Untested proposal |
| `integration` | Data integration | Combine datasets/modalities or correct cross-dataset effects. | Untested proposal |
| `alignment` | Sequence alignment | Compute sequence/read alignments; supplied alignments alone are insufficient. | Untested proposal |
| `quantification` | Quantification | Estimate abundances or feature measurements from lower-level observations. | Untested proposal |
| `enrichment` | Enrichment analysis | Test or score sets/pathways against an explicit background or ranking. | Untested proposal |
