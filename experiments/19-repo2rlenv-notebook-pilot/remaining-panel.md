# Remaining seed-panel intake

On 21 October the user requested runs of the remaining notebooks from issue 18.
Use the current autonomous pipeline under issue 19. This does not restore the old
panel's hand-selected task directions, worker harness or partial-credit contract.
The worker must derive eligible endpoints and the task from each original source.
The user subsequently authorized parallel launches. Use at most two reserved
Iris CPU hosts and two Daytona sandboxes total, one per campaign, within the
existing $100 aggregate authorization. Preserve first outcomes and verify cleanup
for each campaign.
PyRadiomics campaign 018 was submitted on 21 October at 15:44 UTC, while the
MDAnalysis host was finishing its archive. Factory revision:
`bd0c81c640c1be3d7b30a958ab84264807d9d18a`. It ended with an input-snapshot controller error in setup; host and sandboxes
are now terminal/absent. This is an infrastructure failure, not a scientific
rejection; see [original receipts](autonomous-runs/018/README.md).

The pinned source identities and admission findings are in
[remaining-panel-intake.json](remaining-panel-intake.json). All seven remaining
sources were fetched and matched their original issue-18 SHA-256 hashes.

| Seed | Current state |
| --- | --- |
| PyRadiomics | Campaign 018 failed during the controller input-snapshot check in setup. General converter profile v4 records and ignores boolean `editable`/`deletable` metadata while preserving ordered executable AST. No biological execution yet. |
| scikit-bio IL6 | Unsupported conversion: embedded IPython shell commands, including a conditional install. No source repair or scientific execution. |
| Harvard bedtools | Unsupported conversion: Bash kernel. Earlier coordinate/assembly concern remains unresolved. No source repair or scientific execution. |
| methylKit | R Markdown; R support deferred by the user. |
| QFeatures | R Markdown; R support deferred by the user. |
| xcms | R Markdown; R support deferred by the user. |
| phyloseq | R Markdown; R support deferred by the user. |

The user chose supported Python seeds first and deferred R support. Unsupported
formats are pipeline coverage gaps, not evidence of broken science or validated tasks.
The Bash path also needs support before the bedtools analysis can be tested.
The scikit-bio notebook was previously set aside as an out-of-distribution choice;
it is included in this requested panel's intake, without silently replacing it.

Scanpy's earlier pilot used the newer notebook explicitly selected by the user;
do not revert to the legacy issue-18 source. MDAnalysis rerun 017 passed setup and fresh reference replays after a recorded
empty-response retry, then reached construction and grading. It ended with
`independent_comparison_unresolved`: the grader did not accept the independent
implementation. No native solver ran. The host is terminal and all four stage owners were absent in a fresh provider
inventory; see [original receipts](autonomous-runs/017/README.md).
Original failure 015 remains preserved. COBRApy outcome 016 is preserved;
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
