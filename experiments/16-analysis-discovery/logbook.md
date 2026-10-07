# Logbook

## 2026-10-06 — user-directed extension and review state

The user requested exploration of raivivek/awesome-biology and an HTMLPreview
results explorer like issue #5. Treat the curated-list route as a separate,
purposively selected extension: inspect its link inventory, follow up to six
promising paths to concrete analysis documents, and record intervening indexes.
Do not pool its yield with the frozen initial routes. The user explicitly retains
the completion decision: keep issue #16 OPEN and findings provisional until they
are satisfied. Publishing a reviewable preview does not complete the experiment.

## 2026-10-06 — setup

Read issues #16 and #5 and repository guidance. Remote main matches the checkout.
No prior issue #16 comments or implementation were found. Selected three routes
to contrast general code hosting, curated R documentation, and a notebook/data
platform. Fixed provisional labels and screening rules in protocol.md before
candidate review. Initial load 0.40, MemAvailable about 4.67 GiB. No child agents.
Only lightweight retrieval, file editing and small manifest calculations planned.

## 2026-10-06 — user-directed Kaggle route correction

The user pointed out that biological competitions provide a better entry point
than generic notebook search. Preserve the original four-query search as a
failed discovery procedure (two document leads, unreadable in web extraction),
not as a verdict on Kaggle. Add a competition-first cohort targeting ten notebooks:
first identify biology competitions, then inspect their Code tabs and query by
competition name. Begin with protein function, RNA and single-cell challenges;
cap at four competition discovery queries plus four notebook-resolution queries.
Record competition/data clusters and any access or competition-rule limitations.
This amendment is prospective for the new cohort; do not pool its yield with the
original search. No competition participation, submission or paid compute.

Competition-name searches yielded identifiable notebooks and linked data pages,
although Code tabs were empty in the web reader. A public read-only kernel pull
for the TensorFlow CAFA notebook returned source (HTTP 200, 87,031 bytes) without
credentials. Extend static source inspection to ten competition-linked notebooks,
with up to three per competition (overriding the original two-per-study rule for
this cohort to expose within-challenge repetition). Select the first three CAFA
leads, two OpenVaccine leads including the earlier LGBM hit, first three single-cell
perturbation leads and first two multimodal leads. No ranking by leaderboard score.

Provisional taxonomy needs explicit RNA biology and cellular phenotyping labels:
RNA stability is not gene-expression analysis, and cytometry is not broad
proteomics. Retain the original eight labels and add these two, reporting both
8-label and 10-label breadth. These additions were prompted by candidate review.

Survey opened the Bioconductor workflow landing page, marimo gallery and the two
linked notebook-pipeline reports. The workflow page redirects discovery to
workflow packages. The gallery includes general demonstrations and simulation;
its presence alone is not evidence of an observed-biological-analysis corpus.

## 2026-10-06 — inspection findings and explorer checkpoint

Preserved the 30-document main comparison, the two original Kaggle access failures,
four targeted probes, and four newly reviewed curated-list documents (40 total).
Six selected awesome-biology paths yielded four concrete documents; three passed
static criteria. Retained two unresolved index/access paths without inflating the
document denominator. Single-cell index rediscovery of B07 is recorded as overlap.

GitHub within-repository choices were purposive for biological breadth, deviating
from a strict returned-file order. B05/B06 initially appeared to converge on a book;
resolving the specific H3K9ac and NF-YA examples showed distinct studies within one
tool family. No claim of globally deduplicated analysis code follows.

Saved metadata and own observations rather than republishing full reader extracts.
Original extracts remain temporary only. Input source bytes, browser caches and
biological data are not durably archived; source hashes cannot substitute for them.
No analysis execution, independent scientific validation or task authoring occurred.

Built an offline HTML explorer with separate cohorts, coverage drilldowns, source
limitations and filtered CSV export. The ongoing-review state is prominent. The
user authorized HTMLPreview publication; retain a commit-pinned preview and leave
the issue open. No research PR or promotion to main is planned at this checkpoint.

Browser verification: the sandboxed launch timed out before checks; an elevated
single-process Chromium attempt failed during page creation. Removing that flag
and using one renderer completed local checks in 2.23 seconds with no page errors
and 111,164 KiB maximum child RSS. No scientific analysis ran in these attempts.
Screenshots were visually inspected at desktop and 390px mobile widths. Final
validation additionally reconciles every matrix cell with candidate records.

The first published HTMLPreview exercised the controls successfully but emitted a
page error because the preview loader evaluated the application/json data script.
Changed the embedded payload to a JavaScript assignment (still escaping `<`) for
compatibility. Local and published UI checks are repeated for this concrete fix.

Public preview at commit 871d12533204242831cd2e3a9d16389dd0d58f1f passed the
same UI checks with zero page errors (2.72 seconds, max child RSS 118,056 KiB).
Recorded the exact URL and checks in evidence/browser-public.json. Browser contexts
were closed in finally blocks and every launched command returned; no persistent
preview server is needed. Remote issue #16 was verified OPEN after publication.

## 2026-10-06 — broader discovery, second pass

User authorized continued discovery and preview updates. Preserve the 40-row
checkpoint and all original cohorts. New scope: up to twelve candidate documents
across challenge expansion, package vignettes/curated paths, Quarto, marimo and
Hugging Face. Record searches with no useful document and access failures; do not
force every route to contribute positive examples. Add biology labels only when
actual documents justify them, while retaining original 8/10-label summaries.
No source execution, biological data downloads, cloud spend or child agents.

User expanded the discovery allowance to 100 candidates. Interpreted as 100
unique candidate documents overall, communicated in chat. The twelve-document
second-pass cap is superseded; original cohorts stay frozen. Expand by new biology,
workflow and route, not by filling quotas with mirrors. Discovery-only permission
continues; no biological execution or paid compute is implied.

The expansion reaches 100 candidate documents: 91 substantive static inspections,
eight access-only records and one pending inspection. Computed assessments are
65 apparently suitable, 25 unresolved, nine excluded and one not reviewed. These
include the unchanged first 40; the original 30-document comparison remains
21 apparently suitable, five excluded and four unresolved.

Acquisition inputs were checkpointed at 95a84cd (core), 52b7715 (catalog) and
752e5f1 (embedded PlantCV sources). Each request was capped at 4 MB and 12 seconds,
run sequentially under the shared nonblocking lock. Earlier lock contention
caused immediate aborts; successful retrieval happened after later resource
checks. The three successful batches started/ended at 20:23:57/20:24:00,
20:27:27/20:27:34 and 20:28:38/20:28:41 UTC, exit 0. Peak RSS was 27,684,
49,744 and 48,120 KiB. Tree metadata ran 20:25:29–20:25:33 UTC, exit 0,
45,352 KiB peak RSS. Load checks remained below 1.5 with >4 GiB available.
All commands returned, no detached acquisition workers remained.

Direct Bioconductor requests returned 403, while some rendered pages were
readable through the web reader. Scirpy's 3k raw notebook and PlantCV multi-object
notebook exceeded the cap; the former was screened through rendered documentation,
the latter remains access-only. Allen rendered 404s were recovered via repository
trees and pinned sources. Preserve the original failures alongside recovery.

Review noted duplicate studies, untraced DREAM prediction assets, Geneformer
prepared-input/model mismatches, two Allen examples that overwrite an older
dataset assignment, and conceptual/unfinished Quarto decks. None were executed.
The 13-label display keeps original 8/10-label comparisons fixed. The explorer
now separates identified counts, substantive inspection and pending access work.

Local browser validation passed at 20:34:46–20:34:50 UTC, exit 0, maximum child RSS 114,080 KiB. Checked all counts, new stage filters, expansion drilldown, frozen Kaggle export IDs, every coverage cell, offline reload and desktop/mobile layout. Desktop screenshot inspected. The source-only metadata clarification afterward changes hosting/format/path labels, not counts or UI behavior. No issue closure or promotion is requested.

Published 100-candidate preview at 68ae856a26acf4b08369431e443163f61d53e5a2 passed public browser checks at 20:36:15–20:36:19 UTC, exit 0, no page errors, maximum child RSS 119,748 KiB. Counts, stage filters, export, every coverage cell and desktop/mobile layouts passed. Evidence is in evidence/browser-expansion-public.json. Browser closed in finally and command returned. GitHub issue #16 was verified OPEN; no issue comment, closure, PR or merge was performed.

## 2026-10-06 — resolve remaining inspections and report on the issue

User requested continued work and explicitly requested progress recording on
issue #16. Posted and read back comment 6025488796 with the existing published
checkpoint and source-recovery status. Continue substantive checkpoint comments;
the instruction does not authorize closing the issue.

Initial metadata recovery used an incorrect LoveMI/DESeq2 repository guess and
failed with 404 at 21:06:43–21:06:44 UTC, exit 1, peak RSS 45,096 KiB. Official
package/search evidence identified thelovelab/DESeq2. Corrected retrieval ran
21:06:56–21:07:00 UTC, exit 0, peak RSS 45,420 KiB. Source inputs were checkpointed
at 4b1dc40. Twelve source/helper documents were retrieved at 21:07:53–21:07:55 UTC,
exit 0, 1.84 seconds and peak RSS 55,212 KiB. Commands held the shared lock,
used one worker and thread limits, and returned without persistent workers.

All nine previously pending records now have static inspections. Five became
apparently suitable, two excluded, two remain unresolved. Overall: 100 inspected,
70 apparently suitable, 19 unresolved, 11 excluded, zero executions. Preserved
the original first 40 records. Changes to 14 extension records, including
additional input tracing, are explicit in the before/after ledger. The report
records version differences, source recovery limits and negative findings.

Browser validation attempt aborted immediately because the shared heavy-work lock was occupied; no Playwright process started. No retry/polling was performed. Current manifest/hash checks and unchanged-identity checks pass; browser verification of the revised data/text remains pending, separate from the previous successful preview. The 70 suitable records have 54 provisional study-cluster labels, including 11 repeated labels; this is not a validated independent-study count.

Correction after the source-recovery count audit: O01/O02 explicitly had no notebook cells recovered, but the builder default had treated all first-40 records as substantive inspections. Preserve those records and apply evidence/legacy-review-stages.json in current summaries. The prior 91-inspected checkpoint actually had 89 substantive inspections plus two legacy access-only leads. Current counts are 98 substantively inspected and two legacy access-only leads, with 70 suitable, 19 unresolved and 11 excluded. Original main-comparison denominators and suitability counts do not change. The earlier 100-inspected statement above records the superseded intermediate calculation.

Published source-recovery checkpoint 7bedce5beda1aebbfc3ad047c8056409359bdce4. Posted the updated counts, explicit legacy-stage correction, findings/preview links and browser-validation limitation at https://github.com/Open-Athena/biotasks/issues/16#issuecomment-6025604822. Read-back exactly matched the inspected draft, and issue state remained OPEN. README separates latest preview from earlier browser-validated checkpoint.

## 2026-10-07 — Unified results presentation

At the user's request, the explorer presents the full 100-document collection without a 30-document/expansion split, cohort filter, or chronological progress narrative. Route totals and coverage aggregate all candidates. The curated-index drilldown includes DREAM paths. Historical manifests, cohort provenance and baseline calculations remain in research artifacts; assessments are unchanged. Issue body will serve as the current findings summary, with completion retained by the user.

Local browser check passed (14:37:20–14:37:24 UTC, exit 0, maximum child RSS 115836 KiB, estimated working set 450 MiB): route filtering and exact CSV IDs, all-document and curated drilldowns, every coverage cell, evidence details, sorting, empty results, offline reload and desktop/mobile layout. No JavaScript errors. One redundant closing div was subsequently removed before publication; public validation checks the published revision.

Published revision `b4c73c84811dc5b9999a0c0cc9a05e4c440029a1` passed public HTMLPreview browser checks at 14:38:51–14:38:55 UTC (exit 0, peak child RSS 120508 KiB); browser closed normally. Evidence: `evidence/browser-unified-public.json`. Issue body replaced with current combined findings and permalink, read back exactly; OPEN state and agent-generated label verified. Saved body: `evidence/issue-body-current.md`.

## 2026-10-07 — Four UI options

Published `style-options.html` at `164861177de5ed9794cda0f85f3cdfa41d31e0e7`: Editorial, Atlas, Lab console and Botanical share the unchanged candidate payload and interactions. `build_style_options.py` derives them from the current explorer plus `style-options.css`. Default explorer is unchanged pending user selection. Public browser checks passed for all four styles and five views at desktop/mobile widths, counts and suitability filtering; no page errors. Run 14:44:49–14:44:55 UTC, exit 0, peak child RSS 124924 KiB, 450 MiB estimate, browser closed normally. Evidence: `evidence/browser-style-options.json`. Added comparison link to issue body and verified exact readback and OPEN state.

## 2026-10-07 — Structural design alternatives

Replaced palette-only comparison as the issue's primary design link with five distinct interaction layouts: source-card catalog, sidebar dashboard, coverage-first matrix with drilldowns, long-form editorial report, and searchable split-pane inspector. All consume the same normalized explorer payload. No forced heading line break; default results explorer remains unchanged pending user choice. Builders and templates are branch-local.

First public check at `31d827f` failed on dashboard source-table mobile overflow (exit 1); browser closed through finally. Fixed grid-child minimum width at `86d3bf8a64b6a212a4c4529500a90f5567dae1f6`. The public rerun passed 14:57:14–14:57:17 UTC, exit 0, peak child RSS 116896 KiB (450 MiB estimate). Checks cover all five layouts at desktop/mobile widths, filtering, details, CSV exports, empty states, reset and matrix navigation; zero page errors. Public evidence: `evidence/browser-layout-options.json`. Issue body updated and exact readback/OPEN state verified.

## 2026-10-07 — Methods-first workbench

Applied the user's preferred dark workbench style across Methods, Sources, Coverage, Findings and Source index. The opening methods map documents all 11 recorded routes and four common screening steps, with counts and route-to-source drilldowns. Every candidate field is rendered in the complete record; JSON export preserves the normalized payload. The awesome-biology inventory remains accessible. Scientific assessments are unchanged.

Published revision `13735c0f64955f9fdb75983c70c7113f89c8c98f` passed public checks at 15:06:26–15:06:30 UTC (exit 0, peak child RSS 115876 KiB, 450 MiB estimate). All five views fit desktop/mobile widths; all route drilldowns, manifest export, detail metadata, filters, coverage and curated drilldowns passed without page errors. Browser closed normally. Evidence: `evidence/browser-workbench.json`.

GitHub GraphQL issue edits failed twice with server errors; REST PATCH returned an empty response parse error. Subsequent readback: issue body matches intended update = False; issue state = OPEN. Exact pending body saved in evidence/issue-body-pending.md; published body preserved separately.

## 2026-10-07 — Candidate definition and HF surface coverage

Clarified the screening unit before the methods diagram: one selected analysis document, not a repository or platform inventory. All route cards now label counts as selected for this collection; GitHub's 12 is explicitly not a population estimate, and other routes can lead to GitHub-hosted files. Added HF repository-notebook, article and Spaces distinctions using primary platform documentation, with unsearched surfaces explicitly labeled. No new candidates or assessment changes.

Published revision `37bdad211253826fd9b7b8fdb47705f7576454c5` passed public browser checks at 17:55:54–17:55:57 UTC, exit 0, peak child RSS 116760 KiB, 450 MiB estimate; no page errors and browser closed normally. Checks include candidate-definition text and the three HF surfaces, all route drilldowns and desktop/mobile behavior. Evidence: `evidence/browser-candidate-definition.json`. Prior pending evidence push recovered. Issue body now updated successfully, exact readback verified, issue OPEN. The earlier issue-body-pending.md remains historical evidence of the server-failed attempt and is superseded by issue-body-current.md.

## 2026-10-07 — Remove redundant Findings view

User approved removing Findings. Navigation now contains Methods, Sources, Coverage and Source index. Preserved distinct study-reuse and unresolved-input conclusions beside the coverage matrix; removed the duplicate narrative/source directory. Published revision `40bdd07e5f4562f03e451dedf465466794901057` passed public browser checks at 18:00:00–18:00:03 UTC, exit 0, peak child RSS 114568 KiB, 450 MiB estimate. Four-tab navigation, desktop/mobile layout and existing source interactions passed; browser closed normally. Evidence: `evidence/browser-four-tabs.json`. Updated issue body and verified exact readback and OPEN state.

## 2026-10-07 — Project-entry provenance

At user request, separated tool/project entry from within-project document retrieval. Saved four project mappings and exact recorded search queries in `evidence/tool-discovery-provenance.json`; the workbench now displays the mappings in Methods and relevant source inspectors. Renamed the UI group to Selected-tool tutorial inspection while retaining manifest keys and assessments. Explicitly limited 24/28 to the four selected catalogs, not comparative discovery efficiency.

Public preview `89bbd01f896c2e78b6acd72b47a9de1b13c0a00e` passed browser checks at 18:04:45–18:04:49 UTC, exit 0, peak child RSS 115424 KiB, 450 MiB estimate. Four-project table, counts, source interactions and desktop/mobile views passed, with no page errors; browser closed normally. Issue body updated with provenance evidence and exact readback verified; issue OPEN.

## 2026-10-07 — Fixed issue-5 repository audit and composition clarification

User requested renaming the 100-document matrix to Collection composition, collapsing the HF methods detail, and checking notebook coverage using issue #5's already categorized repository inventory. Imported the 1,014-source top-300 union and unchanged labels/rankings from `4d1efa0593f40be515b0428fa30be783a54407e9`. All 871 GitHub mappings had recorded revisions; 143 unmapped sources remain explicit.

Initially interpreted notebooks too narrowly as Jupyter. User corrected this during acquisition. Stopped only this task's scanner with SIGINT after 298 records (shell exit 130), preserving that incomplete attempt and scanner in `repo-notebook-audit/ipynb-only-incomplete/`. No counts from it substitute for the corrected run. Broadened to Jupyter, R Markdown, Quarto, Sweave/knitr, Wolfram, MATLAB Live Script, Livebook, .NET Interactive, R notebook exports and bounded marimo/Pluto/Jupytext source-signature probes. Scanner/input checkpoint `c5d9d62` preceded the corrected run.

Corrected run: 18:15:57–18:21:36 UTC, exit 0; one worker with lock and resource guards; estimated 180 MiB, reported peak self/child RSS 101012 KiB each. Checked all 871 revisions. Results: 405 with supported files/signatures, 465 none detected, 1 unknown (truncated epam/ketcher tree); 143 unmapped. Formats overlap: 196 Jupyter, 186 R Markdown, 37 Sweave/knitr, 10 Quarto, 3 marimo, 3 Wolfram, and 1 each MATLAB Live Script, .NET Interactive and Jupytext. Detections occur under 21/22 original labels; RNA structure has none detected among its three repositories. These are repository labels and filename/signature detections, not validated analysis content. 118 prefix probes, including three recorded HTTP 416 errors; 100836 other text files unprobed.

Offline summary and independent accounting validation passed. All input hashes, identities, repository revisions, primary labels and ranking memberships match issue #5. Local browser checks on `a912ced` passed the five views, collapsed HF detail, repository domain/format/status filters and existing source interactions. Public validation and issue publication follow.

User additionally asked about the rendered DESeq2 vignette. Verified the linked devel page as a worked RNA-seq analysis and explicitly included it as a Methods example. L39 already preserves the release-page identity and pinned source review; the live devel version is not assumed identical. The audit detects DESeq2 through R Markdown and does not classify arbitrary HTML as notebooks. Evidence: `evidence/deseq2-rendered-example.json`.

Published final UI/data revision `dc614d1b0215b3b9e9d0174b02200ada7daba711` passed public browser validation at 18:24:41–18:24:46 UTC, exit 0, peak child RSS 121800 KiB (450 MiB estimate), no page errors. Checked all five views at desktop/mobile widths, fixed inventory counts, R Markdown and domain filters, collapsed HF detail and existing source navigation. Browser closed normally. Issue #16 body updated with results/protocol/validation links, exact readback and OPEN state verified; issue #5 untouched.

### 2026-10-07 — Alternative-host search for all 143 unmapped identities

- User requested all alternative sources, not only Bioconductor. Preserved the issue-5 identities and original primary-domain labels; checkpointed the first pass at 957c241, recovery at 9366b2a, documentation follow-up at f2a482d.
- Searched all 143 through Bioconductor pages/mirror, GitLab/Bitbucket trees, pinned recipes, PyPI/MetaCPAN metadata, bounded distribution archives and declared documentation. Final accounting: 97 source identities with document locators, 2 tutorial-lead-only, 44 no detection under bounds; 21 encountered at least one access/budget limit, including recoverable failures. Locator positives are 96 Bioconductor sources plus cell-eval2's linked ArcInstitute/cell-eval notebook. Subread and MEME have tutorial leads.
- Preserved dependency-link false positive from scCoord in raw evidence, excluded generic PyTorch tutorials through an explicit adjudication. Recovered GitHub URLs are links, not necessarily ownership/version equivalence. Current metadata and historical repository scans have different time anchors and detectors; do not combine into an apparent uniform notebook fraction.
- Runs completed exit 0, maximum recorded Python RSS 61,860 KiB (250 MiB estimate), sequential and under the shared lock. Archives were inspected without extracting or executing; packaged fixtures may have been received. Qualimap tree was rate-limited; archive caps and blocked sites remain unresolved. The original 100 candidates and 871-repository observations are unchanged.
- Added an alternative-source evidence section to the existing repository view, with all 143 rows, original-domain/result filters, document links, request fingerprints, failures and archive/tree limits. Kept selected-document screening separate. Issue remains open for user review.

- Published HTML revision 45f74e7216afe0e1bb45c7cba81de5750301527c passed local and public HTMLPreview browser checks, including all 143 rows, result filtering and expanded evidence. Issue body published and read back exactly; state OPEN and agent-generated label verified.

### 2026-10-07 — Unified current-state source coverage

User requested that the website present current results, without Git/non-Git or chronological search-pass divisions. Replaced the split audit interface with one 1,014-source inventory, shared text/domain/format/result filters, unified domain counts and per-source expandable evidence. Counts are 502 identities with a document located, two tutorial leads, 509 no detections and one unresolved search. These are heterogeneous discovery-evidence counts, not a comparable detection-rate estimate, unique-document count or scientific validation. Original acquisition records remain unchanged; methods and limits live in collapsed details. Methods links to the unified view.

Local and published HTMLPreview checks passed for 03c179538337986c61c64c81f9a23f1bb8ed460f, including desktop/mobile layouts and unified filters. Issue body updated, read back exactly, OPEN with agent-generated label.

### 2026-10-07 — Separate discovery-methods and inventory sites

User approved two linked sites organized around different research questions. workbench.html now opens discovery methods, with selected-source inspection, collection composition and the curated source index. inventory.html opens the complete 1,014-source inventory with shared search/domain/format/result filters. Each has its own title, navigation and footer, with reciprocal links that preserve the HTMLPreview commit URL or work offline. Both remain current-state presentations sharing one builder and visual template. No discovery evidence or screening classifications changed.

Both sites passed local and public browser checks at b8fba55207b32c71bf1f274fc7e9e7dfb9c4c5be, including reciprocal HTMLPreview links, filters and desktop/mobile layouts. Issue body updated and verified exactly; OPEN and agent-generated label confirmed.

### 2026-10-07 — Canonical authoring documents for LLM input

Consolidated same-version, same-directory Bioconductor vignette representations by document stem. Authoring formats take priority over rendered output and extracted R scripts; HTML remains an optional output reference. No arbitrary repository basename pairs or distinct versions are merged. Underlying discovery observations remain intact.

For alabaster.matrix 1.12.0, inspected the 281,000-byte source archive without installation/execution. DESCRIPTION declares knitr, the Rmd declares knitr::rmarkdown with BiocStyle::html_document. The published userguide.Rmd hash equals the archived vignettes/userguide.Rmd hash. Added that verified source and grouped Rmd/HTML/R into one entry. Other missing authoring sources remain explicitly unrecovered; no Rmd links were guessed. Source-level totals remain unchanged. First browser assertion selected the project link instead of the primary document link; corrected that selector and reran.

Canonical grouping and both-site browser checks passed locally and on public HTMLPreview at 52c573b532d4f4fa5fff4ca666a2a6ecead0e9f0. Issue body read back exactly and remains OPEN.
