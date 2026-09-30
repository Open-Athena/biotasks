# Research method and consolidation

[Catalog](README.md) · [Selected sources](sources.md)

The [research checkpoint](https://github.com/Open-Athena/biotasks/tree/aabc8012f4b23f9bd48cd8ea108b9e2efdc39cf2/experiments/7-biology-pitfalls)
preserves the issue scope, logbook, software-record selection and validation
evidence behind this synthesis.
The [subsequent review checkpoint](https://github.com/Open-Athena/biotasks/tree/94f5aa685bc3b809335b26b5270c6244a029b372/experiments/7-biology-pitfalls)
preserves the independent report, corrections and initial hypothesis entries.

## Question and boundary

Catalog possible changes to computational biology code or analysis artifacts,
drawing on literature, documented examples and explicitly labeled hypotheses.
Include valid artifacts with opportunities to improve
robustness, reproducibility, efficiency or maintainability. The catalog considers
software engineering, statistics/ML and biology separately from the benefit of a
change. Its unit is an opportunity under stated conditions, not a universal rule
or a count of bugs.

This is a bounded, purposive synthesis for
[issue #7](https://github.com/Open-Athena/biotasks/issues/7), conducted on
2026-09-30. It does not establish task verifiability, training suitability, or
the necessary form of teacher demonstrations. Those design questions are tracked
in [issue #11](https://github.com/Open-Athena/biotasks/issues/11); catalog inclusion
must not be read as acceptance into a task release.

## Search strategy

The starting sources were the four biological reviews/tutorials linked in the
issue and SERA §3.1. Searches used a general web search engine, followed by
publisher, PMC, institutional-repository and author pages. There was no native
PubMed/Scopus/Web of Science systematic database search. Searches were
English-language and had no prescribed publication-year window; the selected
publications span 1995–2026. This describes the selected corpus, not complete
coverage of that interval.

The following records the principal search routes and representative queries.
Exact-title/author/DOI refinements located primary texts and accessible versions.
The search did not maintain a complete screened-hit ledger, so no flow diagram,
screening denominators, or quantitative recall estimate is claimed.

| Route or query | Selected sources |
| --- | --- |
| `computational biology common errors literature reproducibility gene name spreadsheet errors batch effects` | B01–B04 |
| Seed review on genomic ML, then targeted population-structure, feature-selection and imbalanced-classifier papers | B06–B09 |
| RNA-seq design seed and `gene set enrichment analysis pitfalls background gene length bias RNA seq Young 2010` | B10–B12 |
| Single-cell tutorial/cancer seeds, followed by targeted false-discovery, ambient-RNA, doublet, integration and imputation papers | B05, B13–B18 |
| `microbiome analysis pitfalls contamination compositional data differential abundance benchmark` | B19–B21 |
| Allele-specific mapping follow-up and `variant calling benchmarking pitfalls representation confident regions Krusche 2019` | B22–B23 |
| Genome assembly accuracy/contiguity search | B24 |
| `phylogenetics phylogenomics systematic errors model misspecification long branch attraction study` | B25–B26 |
| `proteomics false discovery rate protein inference pitfalls target decoy benchmark` | B27–B28 |
| `metabolomics metabolite identification misidentification pitfalls mass spectrometry isomers` | B29 |
| `bioimage analysis pitfalls segmentation quantification reproducibility community guidelines 2023` | B30 |
| Systems-biology model reproduction audit follow-up | B31 |
| Targeted CV model-selection, original FDR and ASA p-value sources | B32–B34 |
| SERA §3.1 → Defects4J and BugsInPy → reproduction follow-up | S01–S03, S07 |
| Scientific-computing practice and reproducibility guidance, including exact-title retrieval | S04–S06 |
| `BugsInPy Widyasari github pandas bug database`, arXiv recovery, then pinned pandas records and upstream commits | S03, S08–S11 |

## Selection and extraction

Include a source when it supplies an identifiable mechanism, limitation,
intervention or recommendation with a plausible computational-biology application.
Prefer original demonstrations for failure claims; retain original guidance for
benefits such as maintainability that the selected empirical audits do not test.
Access must support the particular claim being made. An abstract-only source
can supply discovery context but cannot support detailed per-defect mechanisms.

An opportunity does not need a supporting publication or established defect to
be retained. Plausible ideas without such evidence are labeled **unvalidated
hypotheses**, with their origin, expected benefit, tradeoffs and validation needs.
A source that inspired an idea is distinguished from evidence that the idea works.
Do not invent a citation or imply an empirical result merely to fill the schema.

For each opportunity, extract the artifact/starting condition, proposed change,
intended benefit, assumptions, evidence type, biological relevance and source
location. The possible change is sometimes a synthesis from a demonstrated
failure rather than an independently evaluated intervention. Entries therefore
state intended benefits, not measured effect sizes, unless the source supports
the stronger statement. No intervention was executed in this research.

I49–I50 are initial hypotheses, not an exhaustive inventory of candidate ideas.
I49 has no supporting source reviewed; I50 develops a discovery direction without
an established application. Their inclusion follows the clarified issue scope:
evidence strength describes an entry rather than deciding whether it may exist.

Separate diagnosis, mitigation and reporting from repair. Where information is
unidentifiable or measurements are absent, code cannot supply the missing
scientific evidence. Valid alternative methods remain admissible under their
own assumptions. Do not turn a publication's preferred method into a universal
requirement or a historical ranking into a present-day recommendation.

## How recommendations contribute

Recommendations are retained as recommendations. They identify useful practices
and conditional risks, not proof that the prior artifact contains an error.
This is especially important for modularity, profiling, documentation and
provenance. Biological applicability inferred from general software evidence is
labeled separately from biological examples actually discussed in a source.

The catalog keeps a recommendation only when the starting condition and intended
benefit are concrete enough to assess. Broad directions such as “improve code”
do not qualify by themselves. A change that only moves complexity, loses
information, or optimizes a metric unrelated to the scientific target may not
be beneficial.

## Following SERA without treating its prompts as a defect taxonomy

[S01](sources.md#s01) motivated the broader scope and led to S02–S03. Its pinned
implementation supplies discovery directions covering interfaces, state,
dependencies, validation, performance and other areas. These directions guided
search; they did not automatically become catalog entries. The inspected script
generates prompts, not a labeled census of observed defects. The full generated
prompt output was not available in the inspected file, and no generation was run.

S02–S03 are selected bug collections. Their existence supports tracing concrete
failures to fixes and tests, but does not establish a representative distribution
of software defects or their frequency in biology. S07 supplies specific
reproduction findings for the software examples in I42–I44. The catalog does not
claim to have independently inspected every defect in either collection.

### What the counts mean

SERA §3.1 describes 51 broad bug types used as deliberately vague prompts.
Its pinned generator contains 30 seed directions and constructs a set from one
initial prompt plus 50 generated prompts. The generated JSON list is absent from
the inspected repository revision, so those seeds are not a recovered list of
all 51 types.

This catalog's 50 entries are selected opportunities at varying levels of detail,
including biological and statistical mechanisms. They are not a consolidation
or comprehensive extension of SERA's 51. Some generic software areas remain gaps
below; no one-to-one coverage audit of the full generated list has been performed.
Counts alone therefore cannot establish broader coverage or higher quality.

To strengthen direct software evidence, the first six pandas patch records were
screened in BugsInPy's pinned snapshot. Four were retained after checking their
metadata and upstream fixes/tests (S08–S11); their biological uses are inferred.
This convenience sample targets data-processing mechanisms, not a distribution
estimate. Record 5's displayed patch overlapped record 4 but disagreed with its
own revision/test metadata, so it was excluded. Record 6 was deferred rather than
interpreting exception handling without its surrounding behavioral contract.

## Consolidation decisions

Merge descriptions when their starting condition, mechanism and useful response
are equivalent; retain separate entries when the estimand, evidence or corrective
decision differs. Source labels do not dictate entry boundaries. The reciprocal
links in the catalog and source register provide the complete source-to-entry
mapping; the table below records the substantive overlap decisions.

| Neighboring observations | Decision and rationale |
| --- | --- |
| B01 and B02 spreadsheet audits | Merge into I01; independent observations of identifier coercion, without pooling incompatible denominators |
| Identifier coercion, changing nomenclature, generic input checks | Keep I01, I02 and I36 distinct: preservation, identity reconciliation and contract checking solve different problems; a validator alone does not resolve identity |
| Batch effects, ancestry, integration | Keep I03, I05 and I15: related adjustment questions with different confounders and biological targets |
| Replication, train/test dependence, feature selection and tuning | Keep I04, I07, I06 and I33: sampling uncertainty, prediction unit and two different uses of held-out information need different repairs |
| Supervised selection and fitted preprocessing | Consolidate in I06: both must respect the prediction setting's information boundary; label-free transforms can also leak held-out information |
| Train/test dependence and distribution shift | Keep I07 and I08: an independent evaluation can still target the wrong population |
| RNA normalization in B10 and B11 | Merge into I10; guidance and mechanistic evidence about the same scaling decision |
| Ambient RNA, multiplets, reagent contamination | Keep I12, I13 and I19: similar apparent mixtures require different controls and mitigation |
| Normalization and compositional network inference | Keep I10 and I20: related relative-measurement constraints, different estimands |
| ROC, imaging, assembly and genomic coverage metrics | Keep I09, I31, I25 and I24: the missing property and required evidence differ |
| Multiple testing and proteomic FDR | Keep I34, I28 and I29: multiplicity, aggregation level and individual-hit confidence are distinct claims |
| Tree-model adequacy and discordant gene histories | Keep I26 and I27: model failure versus history aggregation, even with correct gene trees |
| Executable model completeness, interface examples, provenance and environments | Keep I32, I39, I40 and I42: missing scientific parameters are not interchangeable with usage information, run lineage or runtime setup |
| General profiling and environment caching | Keep I38 and I43: a measurement-led optimization practice versus a specific reuse opportunity with compatibility conditions |
| Seed control and general provenance | Keep I41 separate from I40: stochastic state and cross-runtime limits merit an explicit condition |
| Regression evidence and environment repair | Keep I45 and I42: witnessing the intended defect requires first distinguishing setup failure |
| Contract checks in S04 and S10 | Merge into I36: general guidance plus an observed repair to user-facing error handling |
| Type classification, compound-label indexing and optional return values | Keep I46–I48: dispatch, key interpretation and output structure require different checks; they are not biological nomenclature errors |
| Profiling, chunked processing and shared state | Keep I38, I49 and I50: measuring a bottleneck, a proposed memory strategy and a proposed state-isolation change have different conditions and evidence status |

Entry IDs provide stable citation anchors; their numbering does not imply
importance or a target allocation among areas.

## Access and evidence limits

Some direct PMC/publisher opens encountered anti-bot pages, missing files or
other access failures. Where available, indexed primary-source paragraphs and
captions were inspected; institutional/author manuscripts were used for several
PDFs. The source register makes those routes explicit. The full S03 text was
subsequently recovered through arXiv. No claim relies on an unread supplement, and figure
citations may refer to an inspected caption/discussion rather than visual
inspection of every plotted panel.

One assistant performed the original selection, extraction and consolidation.
A separate reviewer subsequently read all 48 sourced entries, checked targeted
claims against 13 publications and inspected the four upstream fixes. The review
identified missing fitted-preprocessing leakage in I06; the revised entry now
covers this mechanism. This targeted review is not independent double screening
of the source universe. No re-execution, comprehensive correction/retraction
check or dataset download was performed. Audits concern their sampled material;
simulations and theory establish possibilities under assumptions. There are no
pooled frequencies or claims about how often a BioTasks candidate contains each
problem. Model/API-generated synthesis itself requires review.

Selection favored accessible, well-described mechanisms. The final source set
was checked for traceable entries and concrete conditions, not for saturation of
the literature. Source counts therefore measure documentation breadth, not
independent confirmations or scientific coverage.

## Unselected routes and open coverage

Related compositional-data reviews were discovery context; B20 provides the
selected primary mechanism. Alternative microbiome normalization/method papers
were not synthesized into a universal recommendation. The imaging search
selected B30 for concrete metric mismatches rather than importing an entire
metric-selection framework. Broader evolutionary-model and metabolite-review
results were narrowed to the cited mechanisms. These are scope choices, not
negative quality judgments about omitted work.

Coverage remains limited for structural biology/docking, spatial registration,
metagenome binning and reference taxonomy, long reads/structural variants,
epigenomic peak analysis, proteomic missingness, metabolite quantification,
coordinate conventions, sample swaps, and plant/nonmodel-organism workflows.
General software coverage is selective: concurrency, security, resource leaks,
API evolution and distributed execution remain open areas for sourced entries
or explicit hypotheses; established biological examples are not required for
inclusion. General inference coverage omits many causal, missing-data,
longitudinal, calibration and uncertainty-estimation issues.

UI/browser-specific directions were not pursued without a scientific workflow
application. No ranking, frequency-weighted sampling policy or task-generation
classification is inferred from these omissions. A later extension should add
concrete opportunities, record their evidence status and reconcile overlaps;
there is no predetermined category quota.
