# Breadth expansion — review checkpoint, 6 October 2026

The inventory now contains 100 candidate documents, including the frozen first
40 and 60 additions. Of these, 91 received substantive static inspection; eight
have access attempts only and one awaits screening. These are document counts,
not independent studies, runnable tasks, or validated scientific analyses.
The experiment remains open until the user is satisfied.

## What changed

- Competition-first discovery adds Plant Pathology 2020 and HMS EEG. The GitHub
  HMS notebook belongs to the same challenge as the Kaggle EEG example.
- A community newsletter led to a marimo Scanpy pipeline. It reuses PBMC3k and
  has Quarto/notebook representations, so it adds format evidence, not a study.
- Hugging Face author/model examples yielded two Geneformer notebooks. Their
  biological goals are concrete; exact prepared inputs and model paths remain
  unresolved. Generic platform search was less useful than an author/model lead.
- Following the DREAM olfaction project yielded four paper-analysis notebooks.
  Legacy helpers and untraced local assets prevent positive suitability calls.
- Tool documentation and repository catalogs yielded PlantCV, MDAnalysis,
  Allen OpenScope and scirpy documents. Broken rendered Allen links were
  recoverable as pinned notebook files. PlantCV required following embedded
  nbviewer links to source repositories, not stopping at the tutorial wrapper.
- Quarto extension found both useful analyses and counterexamples: microbiome
  functional-analysis slides have no worked code, and the ML deck is a skeleton.
  Format alone is not evidence of a usable analysis.
- Package-level Bioconductor selection extends beyond the first alphabetical
  workflow sample. Some pages were readable through the web reader while direct
  versioned retrieval returned 403; seven selected vignettes remain access-only.

Plant biology, neuroscience and immunology extend the display taxonomy to 13
labels. Original 8/10-label comparisons use their original label sets. No
original candidate assessment or cohort was changed. Expanded coverage is
purposive and must not be mixed into the original route-yield comparison.

## Repetition and limitations

Shared-study clusters explicitly connect the AdK trajectory examples, PBMC3k,
HMS, DREAM olfaction, Tengeler2020, and the three Arabidopsis RNA-seq chapters.
The simple and color-corrected PlantCV B73 workflows also share a photograph.
Different analyses of the same input remain distinct documents; confirmed format
mirrors are aliases. This is not 100 independent datasets. Semantic duplicate
review and upstream lineage tracing remain provisional.

Static screening checks the question, analytical choices, named input path and
dependencies. It does not test input availability, execute notebooks, establish
scientific correctness, or establish reuse rights. Some exercises intentionally
require filling in code. Rendered documentation can differ from pinned source;
inspection URLs and acquisition failures are retained. Sources over the 4 MB
retrieval cap were not downloaded in full by the acquisition script.

The new acquisition batches took 2.54, 6.93 and 2.86 seconds, with maximum process
RSS 27,684, 49,744 and 48,120 KiB respectively. Tree metadata retrieval took 4.36
seconds and 45,352 KiB. These timings exclude search and manual inspection; no
per-document review duration or provider-cost estimate is available. No biological
input files, model weights, paid compute, or scientific execution were requested.

## Discovery coverage and next work

| Approach | This pass | Remaining limitation |
| --- | --- | --- |
| GitHub/web document search | Original sample plus source recovery | Not an exhaustive repository crawl |
| Biology challenge → notebook | Kaggle expanded from four to six challenge clusters | More challenge families/platforms remain |
| Bioconductor workflows → package vignettes | Both sampled | Versioned-access failures need resolution |
| awesome-biology → tool/project docs | Original paths retained; DREAM followed further | Most root links remain unexplored |
| Tool tutorial catalogs → actual source | PlantCV, MDAnalysis, Allen, scirpy | Within-catalog concentration remains |
| Format-focused search | marimo, Quarto, Rmd/Rnw, ipynb | No evidence of format-wide recall |
| Author/model hub → examples | Two Geneformer documents | HF is not comprehensively searched |
| Papers, citations, supplements → code | DREAM paper notebooks only | No systematic citation or supplement search |
| Other competitions/languages | Not systematically attempted | DrivenData, broader Synapse, Julia/MATLAB and multilingual search remain |

Next: resolve the nine uninspected records, trace the unresolved local inputs,
and compare independent studies before choosing a small execution shortlist.
Review source/data/model terms separately for that shortlist. Any execution
phase needs a concrete resource plan; this checkpoint authorizes none and does
not imply issue closure.

See the [candidate manifest](candidates.json), [computed summary](summary.json),
[interactive explorer](explorer.html), and [original findings](findings.md).
