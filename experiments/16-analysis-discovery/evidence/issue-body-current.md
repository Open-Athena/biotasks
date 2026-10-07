### Current results

[Explore the methods and 100 source documents](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/89bbd01f896c2e78b6acd72b47a9de1b13c0a00e/experiments/16-analysis-discovery/workbench.html). The selected workbench visual style now opens with a schematic of all 11 discovery routes and the four common screening steps. Each route links to its source records. Navigation also provides the split-pane source inspector, coverage and curated source inventory. The four views are Methods, Sources, Coverage and Source index; study-reuse and unresolved-input conclusions sit with Coverage. Every recorded candidate field is available in the complete source record and JSON export. Public browser checks passed for the methods map, all route drilldowns, desktop/mobile layouts, filtering, evidence details and full-manifest export.

A **candidate** is one specific analysis document selected into this screening collection. It may be a notebook, vignette, R Markdown/Quarto document or worked tutorial, and may still be unresolved or excluded. Confirmed mirrors count once; different documents using the same study remain separate. **GitHub’s 12 records are 12 selected documents, not the total notebooks available through repository search.** Other routes also lead to GitHub-hosted material; platform population sizes and recall are unknown.

Hugging Face coverage currently comprises two Geneformer model-repository notebooks. [Blog articles/tutorials](https://huggingface.co/docs/hub/blog-articles) and [Spaces/apps](https://huggingface.co/docs/hub/spaces-overview) are additional discovery surfaces, not yet systematically searched or screened for this collection. An article or interactive page must still be traced to its analytical content, inputs and code; linked versions must be reconciled before counting.

| Measure | Count |
| --- | ---: |
| Candidate documents | 100 |
| Substantive static inspections | 98 |
| Access attempts only | 2 |
| Apparently suitable | 70 |
| Unresolved | 19 |
| Excluded | 11 |
| Analyses executed | 0 |

“Apparently suitable” means promising after static source review, not demonstrated reproducibility, validated science or permission to redistribute. Assessments total all 100 candidates; the two access-only leads are unresolved. Thirteen biology subdomains are used as overlapping labels.

### Research question and scope

Which discovery routes yield useful computational-biology analyses, and what biological workflows and coverage gaps do they reveal? The goal is a diverse, inspectable source pool for task development, building on [source discovery in #5](https://github.com/Open-Athena/biotasks/issues/5).

The collection covers notebooks, R Markdown/Quarto documents, package vignettes and tool examples found through GitHub, biology challenges on Kaggle, Bioconductor, Hugging Face, galleries and curated indexes including [awesome-biology](https://github.com/raivivek/awesome-biology). Hosting, format and discovery route are recorded separately. Selection is purposive: combined route counts describe this collection and do not estimate platform yield or corpus-wide recall.

### Findings

**Project discovery and document retrieval are different steps.** The group formerly displayed as “tool documentation” is now “Selected-tool tutorial inspection.” Its 28 documents come from PlantCV (9), MDAnalysis (8), Allen OpenScope (8) and Scirpy (3). PlantCV and MDAnalysis were named in targeted searches; OpenScope surfaced in an Allen/Neuromatch search batch; Scirpy’s tutorial index was opened directly, with no earlier discovery step established by the saved record. The 24 suitable documents support these selected catalogs, not a ranking of discovery routes or a measured ability to find unfamiliar tools. The methods map and source inspector now expose this distinction. [Provenance and query record](https://github.com/Open-Athena/biotasks/blob/89bbd01f896c2e78b6acd72b47a9de1b13c0a00e/experiments/16-analysis-discovery/evidence/tool-discovery-provenance.json).

- **Biology challenges are useful entry points for Kaggle.** Competition-first discovery connects notebooks to named datasets and biological questions. Generic search also produced two leads whose source content remains inaccessible.
- **Package documentation and curated indexes supply complementary workflows.** Examples include DESeq2 differential expression, phyloseq community analysis, PlantCV phenotyping, immune repertoires, molecular dynamics and xcms metabolomics. Following awesome-biology through documentation and DREAM projects produces inspectable analysis documents rather than just repository names.
- **Document breadth overstates independent-study breadth.** PBMC3k, AdK trajectories, HMS and faahKO recur. The 70 suitable documents have 54 provisional study-cluster labels; these are not 54 verified independent studies.
- **Input tracing remains a bottleneck.** Geneformer and DREAM sources have unresolved processed inputs or model assets. A static DREAM audit found a loader filename mismatch and missing cache/prediction assets; this has not been tested by execution. Some xcms examples have identifiable analytical inputs but unresolved biological relevance.
- **Not every tutorial is a worked biological analysis.** Performance guidance and import/object-structure documentation can fail the screening criteria even when the underlying package is useful.

### Method and evidence

A candidate is one analysis document; confirmed mirrors are aliases. Review records the biological question, workflow, observed/adapted/simulated input lineage, input locations, dependencies, source terms, study reuse and analytical decisions. Source revisions and hashes are retained where available. Upstream source recovery is not assumed to match the version of a rendered release page.

[Candidate manifest](https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/candidates.json) · [Computed counts and coverage](https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/summary.json) · [Source and input audit](https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/resolution.md) · [Protocol](https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/protocol.md) · [Research logbook](https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/logbook.md).

The HTML is a current results document; chronological checkpoints and historical comparisons remain in the research artifacts. The standard-library builder checks identities, required metadata, evidence paths and recorded source hashes. UI checks are separate from biological execution. No paid compute, model calls or source-analysis executions have been performed. Per-candidate discovery/review effort was not fully tracked.

Methodological leads include [Jupyter Agents](https://huggingface.co/blog/jupyter-agent-2), [Jupiter/NbQA](https://arxiv.org/html/2509.09245v2) and [ExeDS](https://aclanthology.org/2022.dash-1.5.pdf): document identity, input recovery and execution evidence must be assessed separately.

### Remaining work and completion

Resolve the 19 uncertain assessments where evidence permits; check independent-study breadth and source/input terms for promising candidates. Discovery approaches are not exhausted: systematic paper-to-code and citation searches, other challenge platforms, and multilingual resources remain untested. Task authoring, native execution and independent validation are separate subsequent stages.

The issue remains open until the user is satisfied. Keep this body current as findings change. Research is preserved on `codex/research/16-analysis-discovery`; this branch is not intended for merging.
