## Final result

The completed discovery study covers **1,014 computational-biology source projects** and locates notebook or analysis documents for **536**. It provides an inspectable inventory with all-format notebook counts per repository, format breakdowns, source evidence and CSV export.

[Open the inventory explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/inventory.html) · [Methods and screened documents](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/workbench.html) · [Repository counts CSV](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/reassessment/repository-counts.csv) · [Full findings and limitations](https://github.com/Open-Athena/biotasks/blob/f7c0e56a3a5dfdb4520f2ecb29e1c335434541d2/experiments/16-analysis-discovery/reassessment/results.md)

## Notebook and literate-document inventory

| Coverage | Distinct documents |
| --- | ---: |
| 454 repositories with detections | 4,057 |
| Additional package, archive and documentation-download locations | 220 |
| **Total** | **4,277** |

Nine rendered-only fallbacks are reported separately. The repository CSV includes **937 checked or linked repositories**, including those with zero detections.

Detected formats include Jupyter, R Markdown, Quarto, Sweave/knitr, marimo, Jupytext, MyST, percent-cell notebooks, Wolfram, MATLAB Live Script and .NET Interactive. Counts reconcile shared collections, verified copies and established paired representations. Per-repository counts sum to 4,090 because copies can appear in multiple repositories; the global repository total deduplicates them. Uncertain equivalences remain separate. These are located source documents across recorded snapshots, not a count of independent biological analyses or executable tasks.

## Discovery findings

Reliable discovery must follow tutorial submodules and separate documentation repositories, even when a project already has a mapped GitHub repository. It must resolve links against redirected documentation URLs, connect known candidate documents to their source projects, and recognize text-based notebook formats. Collection attribution must exclude generic dependency tutorials and theme links, and scope large shared repositories to the linked project content.

Applying these rules corrected **34 source-level false negatives**. For example, scvi-tools has **65** located tutorial notebooks through its linked collection, and MDAnalysis has **38** through its UserGuide. All original detected paths remain represented.

| Source outcome | Projects |
| --- | ---: |
| Document located | 536 |
| Tutorial lead only | 83 |
| None located within search bounds | 306 |
| Unresolved search | 89 |
| **Total** | **1,014** |

## Screening, validation and limits

The selected collection contains **100 documents: 98 substantive static inspections and two access-only leads**, with **70 apparently suitable, 19 unresolved and 11 excluded**. Discovery counts do not imply suitability or scientific validation. No biological analyses were executed.

[Accounting and regression checks](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/reassessment/validation.json) and [public desktop/mobile browser checks](https://github.com/Open-Athena/biotasks/blob/f7c0e56a3a5dfdb4520f2ecb29e1c335434541d2/experiments/16-analysis-discovery/evidence/browser-reassessment-public.json) passed, including counts, exports, evidence inspection and the scvi-tools/MDAnalysis examples.

Discovery is bounded: **495 source records contain access or search-budget limits**. Every project received the reassessment protocol, but the inventory is not an exhaustive census; zero located does not establish absence. The [protocol](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/reassessment/protocol.md), [document registry](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/reassessment/documents.jsonl), [alias evidence](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/reassessment/alias-evidence.json) and [candidate manifest](https://github.com/Open-Athena/biotasks/blob/dd5bc22f54102f6165b2c3e940b2d90a9ddd7880/experiments/16-analysis-discovery/candidates.json) preserve the evidence and counting rules.

Code and evidence are retained on the permanent `codex/research/16-analysis-discovery` branch. This completes the discovery experiment; task authoring, execution, independent scientific validation and pipeline promotion are separate work.

