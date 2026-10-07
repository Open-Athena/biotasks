### Current results

[Explore the 100 analysis documents in HTMLPreview](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/b4c73c84811dc5b9999a0c0cc9a05e4c440029a1/experiments/16-analysis-discovery/explorer.html). The explorer presents one combined collection, with source details, screening reasons, route filters, biology coverage and CSV export.

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
