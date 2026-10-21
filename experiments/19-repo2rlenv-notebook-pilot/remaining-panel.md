# Remaining seed-panel intake

On 21 October the user requested runs of the remaining notebooks from issue 18.
Use the current autonomous pipeline under issue 19. This does not restore the old
panel's hand-selected task directions, worker harness or partial-credit contract.
The worker must derive eligible endpoints and the task from each original source.
Run sequentially within the existing $100 aggregate authorization, preserving
first outcomes. Reconcile completed holds and verify cleanup before new launches.
No extra campaign has been submitted for this panel yet.

The pinned source identities and admission findings are in
[remaining-panel-intake.json](remaining-panel-intake.json). All seven remaining
sources were fetched and matched their original issue-18 SHA-256 hashes.

| Seed | Current state |
| --- | --- |
| PyRadiomics | Prepared campaign 018. General converter profile v4 records and ignores boolean `editable`/`deletable` metadata while preserving ordered executable AST. No biological execution yet. |
| scikit-bio IL6 | Unsupported conversion: embedded IPython shell commands, including a conditional install. No source repair or scientific execution. |
| Harvard bedtools | Unsupported conversion: Bash kernel. Earlier coordinate/assembly concern remains unresolved. No source repair or scientific execution. |
| methylKit | R Markdown; generic R runner/worker-contract support is needed. |
| QFeatures | R Markdown; generic R runner/worker-contract support is needed. |
| xcms | R Markdown; generic R runner/worker-contract support is needed. |
| phyloseq | R Markdown; generic R runner/worker-contract support is needed. |

A question about adding R support is pending with the user. Unsupported formats
are pipeline coverage gaps, not evidence of broken science or validated tasks.
The Bash path also needs support before the bedtools analysis can be tested.
The scikit-bio notebook was previously set aside as an out-of-distribution choice;
it is included in this requested panel's intake, without silently replacing it.

Scanpy's earlier pilot used the newer notebook explicitly selected by the user;
do not revert to the legacy issue-18 source. MDAnalysis rerun 017 is active and
has passed setup and the fresh reference replays after a recorded empty-response
retry. Original failure 015 remains preserved. COBRApy outcome 016 is preserved;
its missing import requires a source repair, which current user policy rejects.

Notebook code permission does not establish permission to redistribute downloaded
data. Keep new downloaded inputs and generated bundles private until their terms
are reviewed. Carry the notebook's source license and original identity with each
case. Factory improvements must remain general; do not manually edit generated
scientific artifacts or repair original source imports.

Converter validation: 27 unit tests passed, including preservation of code with
true/false editing permissions, invalid permission types and continued rejection
of execution-skipping tags. Ruff lint/format passed. The original PyRadiomics
notebook converts with the same ordered executable AST after the previously
supported presentation normalization. These are conversion checks, not a model
run or biological validation. The metadata interpretation follows the
[official notebook format](https://nbformat.readthedocs.io/en/latest/format_description.html#cell-metadata).
