# Provisional analysis-discovery findings

Status: **ongoing research; completion awaits the user's satisfaction**. Issue #16
remains open. Snapshot: 2026-10-06. Stage: discovery and static source inspection;
no analysis was executed, independently validated, or converted into a task.

## Current result

The 30-document main comparison contains 21 apparently suitable analyses, five
exclusions and four unresolved cases. Each route contributes seven promising
examples, but their biology and failure modes differ. The four targeted probes
and four documents reached through awesome-biology are separate extensions.
Including two unresolved original Kaggle leads, the manifest has 40 documents:
26 apparently suitable, six excluded and eight unresolved.

| Route / cohort | Reviewed / unique | Apparently suitable | Excluded | Unresolved | Suitable breadth (10 labels) |
| --- | ---: | ---: | ---: | ---: | ---: |
| GitHub initial | 10 / 10 | 7 | 2 | 1 | 6 |
| Bioconductor initial | 10 / 10 | 7 | 1 | 2 | 5 |
| Kaggle competition-first | 10 / 10 | 7 | 2 | 1 | 4 |
| Kaggle original generic search | 2 / 2 | 0 | 0 | 2 | 0 |
| Targeted gaps, all routes | 4 / 4 | 2 | 0 | 2 | 3 |
| Awesome-biology extension | 4 / 4 | 3 | 1 | 0 | 3 |

“Apparently suitable” requires a biological question, substantive analytical
choices, a specific input path and identifiable dependencies. It does not assert
correctness, recoverable data bytes, an installable environment, or reuse rights.
The [manifest](candidates.json) records the evidence and limitations per source;
[the explorer](explorer.html) filters sources and shows the multilabel coverage
matrix. [summary.json](summary.json) is computed from the manifest.

## Retrieval denominators

The saved initial web responses contain 17 GitHub result rows and 13 generic
Kaggle result rows, including non-document hits. The Bioconductor index supplied
25 package leads. These units differ from reviewed documents: repository leads
can yield multiple documents, while an index or slide result may yield none.
All ten selected GitHub and ten amended Kaggle notebook sources were retrieved;
the original two Kaggle leads were access attempts only. Search result rows and
ordered URLs are retained in `evidence/discovery-*.json` and
`evidence/additional-searches.json`; they are not platform inventory sizes.

## What the routes contribute

In the main comparison, suitable documents cover seven of the original eight
subdomains and nine of the revised ten; metabolomics is missing. GitHub uniquely
adds structural biology and ecology/evolution relative to the other two routes;
Bioconductor adds epigenomics; Kaggle adds proteomics. RNA biology and cellular
phenotyping were added after candidate inspection; reporting the original and
revised denominators prevents that taxonomy change from silently altering breadth.
In each main route the largest subdomain contains three of seven suitable sources
(43%). Multilabel shares can overlap. These are small-sample descriptions.

GitHub's initial web search surfaced repository, topic, notebook and non-notebook
leads. We selected ten documents from six repositories, purposively favoring
biological contrasts within each repository rather than taking the first ten
file paths. G06 is explicitly simulated RNA-seq; G01 uses predicted protein
coordinates; the coral analysis G08 uses adapted observed data. G04 is mainly a
viewer demonstration and G05 lacks an implemented coherent biological analysis.
G07's missing mapping file leaves it unresolved. These outcomes show why repository
relevance and stars cannot substitute for document inspection.

The Bioconductor workflow index surfaced 25 workflow-package leads; the first ten
alphabetical packages supplied the selected document identities. This selection
favored expression analysis. B05 and B06 resolve to different studies in the same
csaw book (H3K9ac versus NF-YA), not two independent tool families. B07's large HTML
failed extraction but its R Markdown source was accessible. B08 and B10 remain
unresolved at the input-recovery stage. Package metadata and rendered documentation
sometimes point to different versions; freeze the intended release before execution.

**The user's competition-first Kaggle suggestion improved this discovery pass.**
Generic search surfaced two notebook identities whose pages were unreadable in
the web extractor. We preserved those as a separate cohort. Four named biology
challenges then supplied ten source-retrievable notebooks via public kernel pull:
three CAFA, two OpenVaccine, three perturbation and two multimodal examples.
Seven passed static screening. K02 has an unresolved parent-notebook output;
K06 stops before an implemented model; K10 is chiefly a resource index. K05's
per-RNA averaging differs from positional prediction and needs methodological
review. K09 is exploratory analysis, not a full multiomic prediction pipeline.
The intervention changed queries and selection, so this is not a causal estimate
of platform yield. Historical search snippets, votes and current pulled versions
can differ; the retrieved metadata records the actual inspected version.

## Awesome-biology extension

The user-suggested [awesome-biology index](https://github.com/raivivek/awesome-biology/blob/deb849cea4c67bbcd2a4a81c4d014888f357831e/README.md)
contains 188 bullet-link entries / 185 distinct literal URLs under our parser.
Those include books, papers, tools, courses and other indexes; they are not 185
analysis documents. We followed six purposive paths, detailed in
[evidence/awesome-biology.json](evidence/awesome-biology.json):

| Path from the index | Outcome |
| --- | --- |
| Tools → scikit-bio → diversity tutorial | A01: suitable toy-data example, diversity metrics, ordination and group tests |
| Tools → Biopython → phylogenetics tutorial | A02: excluded from this pool; tree operations without a developed biological comparison |
| Awesome Single-Cell → Scanpy → PBMC3k | A03: suitable observed-derived clustering and marker-analysis workflow |
| Awesome Biological Image Analysis → EBImage → vignette | A04: suitable cell-segmentation example with package image paths |
| Awesome Computational Neuroscience | School/researcher index; no analysis document resolved in this pass |
| Competitions → DREAM | Reader access error; analysis discovery unresolved |

The single-cell list also points to cytofWorkflow already present as B07; that
rediscovery is not an extra document. The image-analysis list's notebook-gallery
lead returned empty extraction, while EBImage source was recovered through the
GitHub contents API after HTML/raw-reader failures. Thus awesome-biology adds
useful **discovery paths and workflows**, but no additional subdomain among our ten
labels in this pass. Neuroscience exposes a limitation of that taxonomy rather
than demonstrating complete biological coverage. The index's CC0 terms do not
establish terms for linked documents or data.

## Gaps, repetition and priorities

Targeted probes found eCOMET treatment metabolomics (T01) and FELLA pathway/network
analysis (T02). They fill the missing metabolomics label but do not establish
adequate coverage. T01's demo-data provenance remains uncertain; T02's KEGG inputs
need separate terms review. The marimo CAZyLingua example T03 still requires model
and input-asset tracing. Quarto ecology lesson T04 depends on preceding cleaned
inputs that were not recovered as a standalone analysis.

All 40 canonical document identities are distinct; known Colab aliases remain
attached to their GitHub source records. No global near-duplicate detector was run.
Ten Kaggle documents share only four competition clusters, and several GitHub
pairs share a teaching repository. Workflow labels are descriptive, often specific
to a document, so their count is not a calibrated diversity score. Stars/votes are
secondary and platform-specific: neither this sample nor raw popularity identifies
scientifically valid analyses. Within Kaggle, related CAFA tutorials can repeat
inputs despite very different vote counts.

Provisional next priorities are: expand Kaggle by **challenge diversity**; inspect
Bioconductor workflows outside expression-heavy alphabetical selection; follow
curated-list links to concrete image-analysis and less represented biology
workflows; and resolve input/version/terms uncertainties before authoring tasks.
Generic notebook search remains a discovery lead, but its negative reader results
must not be interpreted as absence of biological notebooks. Hugging Face and
marimo/Colab were surveyed as index/hosting leads, not audited as comparable corpora.

## Evidence, effort and reproduction limits

The initial protocol and retrieval scripts were checkpointed before source pulls.
GitHub source retrieval took 8.41 seconds (peak RSS 45,536 KiB); Kaggle retrieval
6.17 seconds (28,364 KiB). These are acquisition-only lower bounds, not review
costs. Manual review time per document and search-provider costs were not measured;
no defensible cost per promising source can be calculated. No paid compute,
competition submission or external model calls were launched.

Source hashes, versions where available, URL inventories, query arguments and
paraphrased observations are retained. Full third-party notebook/document text and
biological data are not republished. Temporary inspection caches are not durable
archives, and a hash alone cannot recover a source. Rendered documentation often
remains unpinned. Offline count reproduction is supported; exact future retrieval
of every source is not guaranteed. See [README.md](README.md) for commands.
