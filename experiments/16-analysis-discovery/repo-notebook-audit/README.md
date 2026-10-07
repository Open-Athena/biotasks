# Notebook and literate-document formats in the issue #5 inventory

This audit reuses the fixed 1,014-source top-300 union from issue #5 at commit
`4d1efa0593f40be515b0428fa30be783a54407e9`, with its original source identities,
primary-domain labels and ranking memberships. All 871 GitHub-mapped repositories
are checked at their previously recorded revisions, not current HEAD. The other
143 sources have no GitHub mapping in the frozen inventory and remain outside
the repository denominator. No new mapping or biological classification is inferred.

## Detection protocol

- Tree-path extensions: Jupyter `.ipynb`, R Markdown `.Rmd`/`.Rmarkdown`, Quarto
  `.qmd`, Sweave/knitr `.Rnw`/`.Rtex`, Wolfram `.nb`, MATLAB Live Script `.mlx`,
  Livebook `.livemd`, .NET Interactive `.dib`, and rendered R notebooks `.Rnb.html`.
- Source signatures: marimo Python, Pluto Julia and Jupytext text documents.
  Probe at most six `.py`/`.jl`/`.R`/`.md` paths per repository whose names contain
  `marimo`, `jupytext`, `pluto` or `notebook`, reading at most 64 KiB each.
  This is a targeted, incomplete check; arbitrary filenames can be missed.
- Exclude paths under `.ipynb_checkpoints`. Record file/blob identity, format,
  detection mechanism, unprobed text-file counts and request failures.

**Present** means at least one supported extension/signature was detected.
**None detected** requires a complete tree without supported detections; it is
not proof of no notebooks. **Unknown** means an incomplete/error tree without
a positive. A positive in a truncated tree establishes presence but only a
lower bound on detected file count. Missing GitHub mappings are **unmapped**.

Extension matches are not content validation. R Markdown/Quarto may be prose-only;
files may be tests, demonstrations or exports. Paired files and exports can
represent the same document. Counts by format overlap. Repository labels are
not independent classifications of the notebooks within them. External Colab
links, submodules, other branches, separate documentation repositories and
unrecognized notebook formats can be missed. Presence does not establish
biological relevance, input access, reproducibility or task suitability.

No biological input files or models are downloaded; no analyses are executed.
The only source content retrieved is bounded text prefixes for signature checks.

## Execution and reproduction

`input-provenance.json` hashes original issue-5 files copied directly from Git.
`inventory.json` fixes the source-to-repository mapping and labels before scanning.
`scan.py` appends one record per mapped repository to `observations.jsonl`;
`runs.jsonl` records resources and timing. Re-running skips saved records.
`summary.json`, `domain-coverage.csv` and `domain-formats.csv` are derived by
`summarize.py`. `validate.py` independently checks accounting, labels, input
hashes, ranking membership and format counts against raw observations.

The scanner was checkpointed at `c5d9d62` before the multi-format run. Budget:
one sequential worker, one recursive-tree request per mapped repository, up to
six prefix requests per repository, 25-second tree/12-second prefix timeouts,
16 MiB tree parsing cap, 64 KiB prefix cap, estimated peak 180 MiB. Use shared
nonblocking lock, thread caps, reduced CPU/I/O priority and per-request resource
guards. Stop on API rate limits. No paid compute or model calls.

The interrupted 298-repository Jupyter-only attempt is preserved separately in
`ipynb-only-incomplete/`. It was stopped when the user corrected the scope and is
not the reported multi-format audit. Its shell exit was 130 (interruption); the
scanner's finally block records non-success as 1.

Results and interpretation are in `results.md`; the issue-16 workbench embeds the
summary and shows per-domain and per-ranking denominators with repository links.
