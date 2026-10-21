# Autonomous attempt 014: validated task and successful blind solver

Factory `e309363c3675a7dff6b9ba3917cd5e370a36cefc` processed the original
Bioframe motifs-to-peaks notebook through every stage with zero operator
interventions and no reused generated task artifacts. All 13 scientific grading
controls passed and review accepted the grader for packaging. Native Harbor
execution then passed oracle (reward 1) and no-op (reward 0) controls; the blind
GLM-5.3 Terminus-2 solver scored 1 without an execution exception.

The pipeline took 3,635 seconds (60 minutes 35 seconds), including its native
trials. The host lifecycle including final export took about 64 minutes. Solver
agent execution took 216.87 seconds (3 minutes 37 seconds), across eight episodes.
The host terminated successfully. All stage and native cleanup receipts passed;
a fresh provider inventory covering the four stage owners and all three native
trial ownership labels found zero remaining sandboxes. Five dollars were reserved,
not invoiced.

Small original receipts and native trial records were downloaded and hash-checked
by the recovery collector. This directory records the pipeline, grading and native
outcomes and a later provider cleanup observation. The generated bundle and full
traces remain in the campaign's private archive; this run has not been published
as a new Hub release.

This establishes one unattended successful execution of the pipeline, alongside
attempt 006's explicit rejection. The notebook is a known development seed, not
a held-out test of generalization. Scientific comparison is supported for this
instance; universal software portability and robustness across arbitrary notebooks
remain unproven. PR #23 remains draft and unmerged, and does not yet contain the
full research runner.
