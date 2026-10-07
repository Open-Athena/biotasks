### Current results

Two linked sites present the research by question:

- [Discovery methods](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/425613f6ddb678c26f05e6ef4a682fffc22aaad9/experiments/16-analysis-discovery/workbench.html): discovery approaches, the 100 selected documents, screening evidence, collection composition and the curated source index. The sample supports qualitative comparison, not a ranking of platform yield.
- [Inventory explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/425613f6ddb678c26f05e6ef4a682fffc22aaad9/experiments/16-analysis-discovery/inventory.html): all 1,014 source identities from issue #5, with unified domain summaries, search, format/result filters and document evidence.

Both use the source-workbench visual style and present current results. Retrieval methods and limitations appear in source details; there are no separate Git/non-Git result sections. Each site links directly to the other.

### Source coverage

The inventory opens on **Overview**, with source-level totals, a format-distribution bar chart and domain summaries. The complete source table and filters are in a separate **Sources** tab. Clicking a format bar or domain opens matching sources. Format counts overlap across sources; they are not counts of unique notebooks.

For LLM input, authoring documents are preferred over extracted code or rendered versions. Checked **all 176 rendered-vignette entries across 96 sources** and recovered **167 authoring documents: 88 R Markdown and 79 Sweave/knitr**, spanning 94 sources. Primary links now point to recovered authoring text; rendered output and extracted R remain secondary representations. The pass preserved source hashes and locators, not a complete downloaded source corpus; no analysis was executed.

Nine documents remain unresolved across edgeR, limma, lumi and multtest. The edgeR/limma Rnw files are PDF-inclusion wrappers, not substantive authoring source. The checked lumi archives contain PDF/R representations; multtest includes an unconfirmed TeX lead. These remain explicit fallbacks rather than inferred R Markdown. [Recovery results and limitations](https://github.com/Open-Athena/biotasks/blob/425613f6ddb678c26f05e6ef4a682fffc22aaad9/experiments/16-analysis-discovery/authoring-recovery/results.md) · [Per-source evidence](https://github.com/Open-Athena/biotasks/blob/425613f6ddb678c26f05e6ef4a682fffc22aaad9/experiments/16-analysis-discovery/authoring-recovery/final-observations.jsonl) · [Accounting and grouping validation](https://github.com/Open-Athena/biotasks/blob/425613f6ddb678c26f05e6ef4a682fffc22aaad9/experiments/16-analysis-discovery/authoring-recovery/validation.json).

The format chart now shows **245 source identities with R Markdown, 197 Jupyter, 77 Sweave/knitr and four with rendered-vignette fallbacks**, plus other formats. Counts overlap and are not document totals. The new **biological-domain chart** switches between sources with a document located and all inventory sources; bars open the Sources tab with matching filters. The detailed domain table is collapsed.

All 1,014 source identities in issue #5's fixed inventory have been searched, retaining their primary-domain labels. Discovery follows repository trees, notebook signatures, package pages and mirrors, archives and declared project documentation.

| Current source-level evidence | Count |
| --- | ---: |
| Document located | 502 |
| Tutorial lead only | 2 |
| None detected under search bounds | 509 |
| Unresolved search | 1 |
| Total source identities | 1,014 |

These counts describe source identities with discovery evidence, not unique documents or validated biological analyses. A document may be established by a file/signature or a link whose target has not yet been inspected. Search depth, detectors and revision dates differ, so the totals are not a comparable detection rate or platform-wide coverage estimate. Domains classify source projects, not document content. No detection does not establish absence.

The workbench exposes domain summaries and one filterable source table, with document links, revisions, request fingerprints, errors and limits in each source's details. Supported formats include Jupyter, R Markdown, Quarto, Sweave/knitr, marimo and other notebook formats, plus rendered vignettes. Tutorial leads include Subread and MEME Suite. Generic PyTorch tutorials reached through scCoord were excluded as dependency-documentation false positives.

[Repository acquisition evidence](https://github.com/Open-Athena/biotasks/blob/03c179538337986c61c64c81f9a23f1bb8ed460f/experiments/16-analysis-discovery/repo-notebook-audit/results.md) · [Package, archive and documentation evidence](https://github.com/Open-Athena/biotasks/blob/03c179538337986c61c64c81f9a23f1bb8ed460f/experiments/16-analysis-discovery/alternative-source-audit/results.md) · [Unified presentation builder](https://github.com/Open-Athena/biotasks/blob/03c179538337986c61c64c81f9a23f1bb8ed460f/experiments/16-analysis-discovery/build_workbench.py). Acquisition-specific records remain available for reproducibility; the website presents the integrated current result. No source analysis was executed. Archives may include packaged fixtures; no standalone datasets or paid compute were requested.

### Selected-document collection: unchanged 100 candidates

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

### Conclusion and completion

Investigation completed with user acceptance on 2026-10-07. Discovery methods and the fixed source inventory are presented as two linked, current-state sites. The methods collection contains 100 selected documents: 98 substantive static inspections, 70 apparently suitable, 19 unresolved and 11 excluded. The inventory covers 1,014 source identities: 502 with a document located, two tutorial leads, 509 with none detected under the search bounds and one unresolved search. Authoring-source recovery checked all 176 rendered-vignette entries and recovered 167 R Markdown/Sweave documents, leaving nine explicit fallbacks.

The investigation supports a practical discovery workflow: identify projects through indexes, challenges and curated resources; inspect repositories and documentation for concrete analysis documents; consolidate representations and prefer substantive authoring source for LLM input. Preserve rendered output when it adds results, and distinguish extracted scripts or PDF wrappers from full authoring content. The purposive sample does not establish a ranking of discovery-method efficiency or platform-wide coverage.

The sites, source evidence and reproducible builders are preserved on the permanent `codex/research/16-analysis-discovery` branch; no merge or pipeline promotion is part of this conclusion. Public browser checks passed for the linked presentation revision. No biological analyses were executed, and discovery or static suitability does not establish reproducibility, scientific validity or reuse permission.

### Possible follow-up investigations

Content-level screening of newly located documents, stronger text-notebook detection, resolution of uncertain assessments, independent-study breadth and source/input terms remain possible follow-ups. Paper-to-code and citation searches, other challenge platforms and multilingual resources are not exhausted. Task authoring, native execution and independent validation are separate subsequent stages, not completion requirements for this investigation.
