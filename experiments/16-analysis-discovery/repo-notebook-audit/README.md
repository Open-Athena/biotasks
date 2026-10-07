# Notebook presence in the issue #5 inventory

Scope: fixed 1,014-source top-300 union from issue #5 at commit
`4d1efa0593f40be515b0428fa30be783a54407e9`. Preserve its primary-domain labels,
source identities and ranking memberships. Scan all 871 GitHub-mapped repositories
at their previously recorded commits, not current HEAD. The other 143 sources
have no GitHub mapping in the frozen inventory and remain outside the scan denominator.

Collect GitHub recursive Git-tree metadata only. A positive is at least one blob
path ending in `.ipynb` (case insensitive), excluding `.ipynb_checkpoints` folders.
A complete tree without such paths is absent. Failed requests or truncated trees
without matches are unknown; positives in truncated trees have lower-bound counts.
Submodule contents, separate documentation repositories, other branches, external
Colab links, R Markdown/Quarto and marimo Python files are outside this definition.
Presence does not establish valid notebook JSON, biological content, input access,
runnability, independent-study coverage or task suitability. No notebook contents
or biological data are downloaded or executed.

Budget: one sequential worker, at most one tree request per mapped repository on
the initial pass, 25-second timeout, 16 MiB response parsing cap, estimated peak
180 MiB. Use shared nonblocking lock, thread caps and reduced priority. Check
resources between requests; stop on rate limits. Preserve each result immediately
and resume only missing records. Inputs and scanner are checkpointed before run.

Report by the original primary domains and ranking routes: total sources, mapped
repositories, present, absent, unknown, and sources without mapping. Fractions use
explicit repository denominators. This measures notebook presence in a fixed,
previously selected software inventory, not population-wide biological coverage.

## Superseding scope: multiple notebook and literate-document formats

The user corrected the initial Jupyter-only interpretation before completion.
The 298-record interrupted run is preserved in `ipynb-only-incomplete/` and is
not the reported audit. Repeat the fixed inventory scan with these detectors:

- File extensions: Jupyter `.ipynb`, R Markdown `.Rmd`/`.Rmarkdown`, Quarto `.qmd`,
  Sweave/knitr `.Rnw`/`.Rtex`, Wolfram `.nb`, MATLAB Live Script `.mlx`, Livebook
  `.livemd`, .NET Interactive `.dib`, and rendered R notebook `.Rnb.html`.
- Source signatures: marimo Python, Pluto Julia and Jupytext text documents.
  Probe at most six `.py`/`.jl`/`.R`/`.md` paths per repository containing
  `marimo`, `jupytext`, `pluto` or `notebook`, reading at most 64 KiB each.
  This is a targeted, incomplete probe; arbitrary filenames can be missed.

Record detections by format and unprobed text-file counts. A complete tree with
no supported detections is **none detected**, not proof of no notebooks. Keep
truncated/error trees without detections **unknown**. Extension hits have not
been content-validated; a Quarto/R Markdown file may be prose-only, and exports
or paired files may duplicate the same document. Report repository presence,
not unique notebook/document counts or analytical suitability. External links,
submodules and other branches remain out of scope. Source-prefix reads are
static metadata/content inspection, never execution; no biological inputs are
retrieved. Per-prefix timeout 12 seconds; max six per repository, one worker.
