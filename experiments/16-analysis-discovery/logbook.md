# Logbook

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
