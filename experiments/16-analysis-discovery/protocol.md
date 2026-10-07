# Analysis-document discovery pilot

Issue: https://github.com/Open-Athena/biotasks/issues/16
Baseline main: `2a1950d239f1ada467c35393991dac87debe35f7` (verified remotely).
Started 2026-10-06, before candidate review. Investigator: Codex; annotations
are assistant judgments, not independent scientific validation.

## Scope and budget

Discovery and static inspection only. Three initial routes: GitHub notebooks,
Bioconductor workflow/vignette documents, Kaggle notebooks. Target ten selected
documents per route; no broad crawler, notebook execution, data downloads,
external model calls or paid compute. Survey Hugging Face and marimo/Colab
indexes as additional leads. Stop a route at ten reviews or after four bounded
discovery queries if access prevents finding ten. Preserve failures.

Use public web search with site constraints for GitHub and Kaggle and the
Bioconductor workflow index for the R route. Initial search vocabulary:
`biology analysis notebook`, `bioinformatics notebook`, `genomics notebook`,
`ecology proteomics metabolomics notebook`. At most four discovery queries per
route; inspect returned order, select biological document leads until ten,
at most two per repository/study. Save selection exceptions and all surfaced
leads, including repositories requiring document resolution. This is purposive,
search-engine-mediated discovery, not native search recall or a random sample.

Provisional subdomains fixed before review: genomics, transcriptomics,
epigenomics, proteomics, structural biology, metabolomics, systems biology,
ecology/evolution. Allow multiple labels; out-of-taxonomy biology is recorded
separately. Record analytical workflows separately. After initial screening,
at most four targeted gap queries, with additions in a separate cohort.

## Evidence and suitability

Unit: one analysis document, with canonical URL and explicit mirror identity.
Shared datasets/studies form a separate cluster, not automatic duplicates.
Track format, hosting platform and discovery index separately. Record question,
analytical decisions, data lineage (observed/adapted/simulated/unknown), input
location, dependencies, source terms, access, and uncertainty.

Apparently suitable means static evidence supports a biological question,
multi-step analysis with meaningful choices, a specific input acquisition path,
and identifiable dependencies. It does NOT mean executed, reproducible, licensed
for redistribution, or ready for task authoring. Missing evidence is `unresolved`,
not a scientific failure. Record source-code and data terms separately; no source
or biological data redistribution is part of this pilot.

Deduplicate canonical document URLs and confirmed mirrors. Count candidates
within each route and in the union; report multi-label subdomain coverage,
dominant-subdomain share, workflow diversity and route marginal additions.
Popularity is secondary: preserve visible signals, do not invent missing counts.
Assess repetition qualitatively; no causal popularity comparison without data.

Save query arguments and response observations, UTC acquisition intervals,
and hash evidence records. Use wall-clock acquisition effort as a lower bound;
manual review time per candidate and provider costs may be unavailable and must
be reported as such. Reproduce counts offline from the frozen manifest.

## Prior-work lesson

Issue #5's live conclusion was read on 2026-10-06: deeper rankings filled some
groups but did not fix vocabulary/pool omissions. Keep this initial sample fixed
and targeted probes separate; repository coverage is not document usability.

## User-authorized breadth expansion, 6 October 2026

The initial caps describe the frozen comparison, not an ongoing limit. The user
expanded the allowance to 100 candidate documents overall. Additional candidates
use the `breadth_expansion` cohort and purposive biology/workflow selection from
challenge projects, package/tool catalogs, community curation and model examples.
Keep the first 40 records unchanged. Preserve original taxonomy comparisons;
plant biology, neuroscience and immunology extend the display to 13 labels.

Distinguish `identified`, `access_only` and `static_inspection`. Count only the
last in inspected coverage denominators. An acquired source is not automatically
an inspected analysis; an access failure is not a scientific result. Retain
excluded and unresolved candidates rather than replacing them to inflate yield.
Record aliases separately from shared-study clusters. A URL-distinct inventory
does not establish semantic uniqueness or independent datasets.

## Candidate unit and platform coverage clarification, 7 October 2026

A candidate is a specific analysis document selected into this screening manifest, not a repository, search hit count or platform inventory. It can be a notebook, vignette, R Markdown/Quarto document or worked tutorial; it need not pass screening. Confirmed document mirrors count once; distinct documents sharing a study remain separate and are clustered. Access-only document leads retain that stage. The 12 records assigned to GitHub describe this selected sample, not all notebooks discoverable on GitHub; other discovery routes also lead to GitHub-hosted sources. Available population size and recall are unknown.

Hugging Face has distinct repository-notebook, blog/article and Spaces surfaces. Only two Geneformer repository notebooks are currently selected. HF biology articles and Spaces have not been systematically searched or screened in this collection. A blog can provide a worked analysis or links to code; a Space can expose an interactive workflow. Neither format establishes reproducibility or suitability by itself. Trace linked artifacts and mirrors before admitting new candidate records. Platform documentation checked on 2026-10-07; see `evidence/hf-discovery-surfaces.json`.

## Project discovery versus document retrieval, 7 October 2026

The historical route labels mix entry methods, platforms and document locations. In particular, `tool_documentation` is a retrieval category, not an independent search engine. Its 28 records come from four selected projects: PlantCV (9), MDAnalysis (8), OpenScope (8), Scirpy (3). The first two were already named in targeted searches, OpenScope surfaced in an Allen/Neuromatch-targeted search batch, and Scirpy's tutorial index was opened directly without a recorded preceding discovery step. See `evidence/tool-discovery-provenance.json` and its source ledger.

The current UI calls this group “Selected-tool tutorial inspection” and presents project-entry evidence separately from within-project document retrieval. Historical manifest keys are retained. The 24/28 suitable count supports these selected catalogs, not comparative discovery efficiency or a ranking of independent routes.
