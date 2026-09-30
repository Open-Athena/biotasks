# Top-300 depth and sparse primary-group coverage

Follow the user's directions recorded in issue #5 before execution: expand all
four lists to 300 canonical sources and compare less-frequent primary groups at
100, 200 and 300, for each route and their deduplicated union.

Use the same September 29 numerical snapshots, source identity conventions and
GitHub candidate universe as the top-200 baseline. Newly collected metadata may
resolve lower-ranked source identities but does not refresh scores or seed the
GitHub ranking. The separate known-repository audit diagnoses discovery gaps;
its additions do not enter this controlled depth comparison. Preserve all saved
first-200 IDs, scores and labels. Record corrections explicitly if evidence
requires changing those identities rather than silently replacing the baseline.

Start from the archived top-200 preparation cache, verifying each imported file
against the published cache manifest. Extend screening to at most 550 Bioconda
package rows, 350 Bioconductor rows, 400 PyPI rows and sufficient candidates from
the recorded GitHub pool. Review every newly selected source's main purpose and
identity. Reuse existing assistant labels; assign new labels from metadata and
primary evidence, making uncertainty and borderline decisions explicit. Keep
one primary group per source and the existing group vocabulary where applicable.

Compare complete group distributions at all three depths. Define the tail with
explicit count bands (0, 1, 2–5, 6–10, >10) and also track groups with 1–5 sources
at top 100 through later depths without redefining that cohort. Show newly
represented groups separately. Counts, shares, represented-group counts and
per-group changes complement these threshold-dependent summaries. Labels are
assistant-assigned and do not establish executable biological task quality.

Budget: sequential public metadata calls for at most 200 added package/source
identities; bounded read-only collection and standard-library analysis estimated
below 200 MiB. Use one worker, the shared resource guard and exact source
checkpoints. No models, candidate executions, paid compute or biological-data
files. Inputs come from the retained HF archive or recorded public metadata;
outputs and follow-up code stay on this research branch. Preserve older HTML
preview permalinks. Validate list uniqueness, numerical preservation, canonical
joins, all depth summaries and the browser before publishing a new preview.
