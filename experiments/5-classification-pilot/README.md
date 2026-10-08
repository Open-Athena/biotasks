# Notebook classification pilot: draft for discussion

Ten purposively selected documents from eight repositories were statically inspected at pinned revisions. Formats include Jupyter, marimo, Quarto, R Markdown and Sweave. The sample tests distinctions and failure cases; it is not representative and provides no population coverage estimate. The published inventory and inherited labels are unchanged.

## Sample assignments

| Source | Scientific fields | Modality/data type | Selected operations |
| --- | --- | --- | --- |
| [G01: Hemoglobin structural analysis](https://github.com/Brunk-Lab/Digital-Upskilling-BioScience/blob/3ea7943222925bd8977af8046ff2f6451135fbe8/Tutorials/DU_Level_0/2_Intro_Structure_Bioinformatics/Basic_Structural_Tutorial.ipynb) | Structural biology | Molecular coordinates | Structural geometry, Descriptive analysis and visualization |
| [G02: E. coli metabolic engineering](https://github.com/Brunk-Lab/Digital-Upskilling-BioScience/blob/3ea7943222925bd8977af8046ff2f6451135fbe8/Tutorials/DU_Level_0/3_Intro_Metabolic_Networks/Tutorial_Workflow.ipynb) | Systems biology, Metabolomics | Metabolite profiles, Growth measurements | Descriptive analysis and visualization, Simulation or mechanistic modeling (exercise) |
| [E01: PBMC3k Scanpy pipeline in marimo](https://github.com/wolf5996/scanpy-done-right/blob/64034862dc8c7fe31b5321b2fdda0604d76495b2/scripts/pbmc3k-default-pipeline.py) | Transcriptomics | Single-cell RNA-seq | Quality assessment and filtering, Normalization and scaling, Feature selection, Dimensionality reduction, Clustering, Marker testing |
| [E05: Arabidopsis genotype sampling and GWAS](https://github.com/wur-bioinformatics/exploratory-data-analysis/blob/3480d294d2bdba9702a68bd8e4f95ec002fd31ca/week4/arabidopsis_gwas.qmd) | Genomics and genetics | Genotypes and sequence variants | Dimensionality reduction (exercise), Association testing (exercise), Data preparation |
| [E09: FlowSOM cytometry workflow](https://github.com/saeyslab/FlowSOM/blob/013247af703e8426cd5d244db34cc88c66f8014d/vignettes/FlowSOM.Rnw) | Immunology | Flow cytometry | Normalization and scaling, Clustering, Biological annotation, Group comparison |
| [A04: EBImage cell segmentation example](https://github.com/aoles/EBImage/blob/5dccf1abc4d15a515058e909b269f88ac6cfc45a/vignettes/EBImage-introduction.Rmd) | Bioimage analysis | Microscopy | Image segmentation, Descriptive analysis and visualization |
| [L09: Calculating the root mean square deviation of atomic structures](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | Structural biology | Molecular trajectories, Molecular coordinates | Structural comparison, Descriptive analysis and visualization |
| [L14: Principal component analysis of a trajectory](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/reduced_dimensions/pca.ipynb) | Structural biology | Molecular trajectories | Structural comparison, Dimensionality reduction, Quality assessment and filtering |
| [L28: Microbiome alpha diversity](https://github.com/microbiome/outreach/blob/ab143c2bf2c9cfd309d2c090a95c197f6df9a94f/quarto/alpha_diversity.qmd) | Microbiome science | Microbial community profiles | Diversity estimation, Descriptive analysis and visualization |
| [L17: visualize unit metrics](https://github.com/AllenInstitute/openscope_databook/blob/eebe00fc15654772249a4cee53e0e3eba55ef413/docs/visualization/visualize_unit_metrics.ipynb) | Neuroscience | Electrophysiology | Quality assessment and filtering, Descriptive analysis and visualization |

## What the pilot changes

1. **Operation role matters.** The Arabidopsis GWAS is a learner exercise, with no implemented GWAS call. Its PCA teaching block is disabled for rendering and replaced by precomputed results. The metabolic tutorial similarly sends learners to an external FBA tool. Report exercises separately from implemented operations.
2. **Upstream work must not leak into coverage.** Neural quality-metric plots do not run spike sorting; molecular trajectory analysis does not run dynamics; downloading an AlphaFold structure does not perform structure prediction.
3. **Data modality cannot always mean assay.** Predicted structures, trajectories and derived community tables are meaningful inputs. Call this facet “Data modality,” retain the original assay separately when evidenced, and track observed/adapted/simulated/predicted/mixed origin.
4. **A method name can hide different scientific questions.** Scanpy marker tests characterize clusters; they do not establish replicated treatment-effect inference. Its README excludes differential expression while its code runs marker tests: preserve the scope distinction rather than erasing either evidence.
5. **Repository scope is not notebook scope.** The Brunk curriculum declares multiple omics areas; its structure notebook does not inherit transcriptomics or metabolomics. The two MDAnalysis examples share a field/modality but have different operations. Four of eight root READMEs support field assignments in this bounded pass; four remain insufficient, even though their sampled notebook contents support labels.
6. **Cross-cutting fields need conservative rules.** Immune origin alone is setting metadata for PBMC expression analysis; explicit immune-population identification supports immunology for FlowSOM. This boundary needs human review. Likewise, Bioimage analysis is a useful browse field, but its relation to cell biology remains open.

## Evidence and status

[Readable vocabulary](vocabulary.md) and [machine-readable vocabulary](vocabulary.json) give stable IDs, definitions and whether each term was exercised in this sample. Untested terms are proposals, not an established ontology. [Notebook annotations](annotations.json) retain field-specific evidence locators, operation roles, withheld labels and provenance. [Repository annotations](repository-annotations.json) use separate README evidence. [Validation](validation.json) checks IDs, vocabulary membership, evidence locators and count arithmetic, not biological correctness.

All ten selected documents have pilot annotations. This says nothing about the classified fraction of the 4,277-document inventory: the sample comes from the separate historical 100-candidate screening collection, and has not been joined to the full registry. Zero additional corpus-wide labels were applied. Assignment review is assistant static inspection, with no independent human review and no notebook execution. Operations listed are selected, not exhaustive.

`source-content.json` and `repository-content.json` are local inspection caches containing upstream text, retained for review but not published. Acquisition records preserve pinned URLs and hashes. Notebook cell locators are zero-based; text line locators are one-based. No biological inputs or source analyses were downloaded/executed. Only source documents and root READMEs were fetched.

## Proposed next decisions

- Keep the field/modality/operation scheme, with operation roles and input origin added as demonstrated by this pilot.
- Review the Immunology versus immune-setting boundary and Bioimage analysis versus Cell biology boundary on these examples.
- Before scaling, add contrasting cases for the untested fields and general infrastructure, and independently review disagreements. Do not infer broad field coverage from this purposive sample.
- The current vocabulary has 18 candidate fields, not a mutually exclusive partition. Report notebook counts by distinct ID and show overlaps; do not sum field counts as a corpus total.
