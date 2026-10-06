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
