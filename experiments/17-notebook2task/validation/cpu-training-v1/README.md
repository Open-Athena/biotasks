# CPU-training recipe variant: native validation

Native CPU validation of a GLM-5.3-generated SETA cytopathology package,
following a parent-reviewed specification. This is a recipe variant, not an
unchanged SETA baseline or a measurement of autonomous authoring success.

The original solution ran successfully and matched the independent parent
implementation. Its grader failed 1 of 9 tests: it asserted at least 30
high-correlation feature pairs, while both implementations computed 21.
The parent patch removes only that unsupported bound; the exact recomputed
count remains required. Raw generation and the failed native-01 run are retained.
The original duplicate-ID mutation was ineffective for interleaved model rows;
the corrected harness guarantees a duplicate within one model before grading.

Native CPU validation completed on October 6, 2026 at 6:39 pm Eastern
(22:39 UTC), on one Iris CPU. Native-02 passes all nine generated tests,
independent parent recomputation, a separate entry-point rerun and all eight
control expectations. The two positive controls (honest output and a 1e-8
probability perturbation) pass. Six negative controls fail: empty output,
perfect-label predictions, shuffled row IDs, fabricated CV metrics, global-scaler
leakage and duplicate IDs. No control failed from a fixture error.

The unchanged generated solution takes 6.325 seconds; its child peak RSS is
170240 KiB (166.25 MiB). The complete validation has a cumulative child peak
of 173936 KiB (169.86 MiB). Each native child was constrained to 2 GiB address
space and 300 CPU/wall seconds; the outer Iris allocation was 1 CPU/4 GiB.
These measurements meet the declared native computation budget. They do not
measure Docker image build time or a solver agent's runtime.

OOF and test probabilities differ from the independent implementation by at
most 2.22e-16, below the specified absolute tolerance of 1e-6 (relative tolerance
zero). The preprocessing-leakage control differs by 0.0527 and is rejected by
the probability check. Logistic regression is selected by mean training-fold
AUC. This verifies the fixed numerical protocol on this observed public dataset;
it does not establish generalization, clinical utility or benchmark difficulty.

Evidence: [native-02 steps](native-02/results/steps.json),
[controls](native-02/results/controls.json),
[independent audit](native-02/results/parent-audit.json),
[repeatability](native-02/results/repeatability.json),
[original failure](native-01/results/native-tests.stdout.txt),
[parent patch](parent-package.patch), and [candidate](candidate/).
The checkpoint before native-01 is 04a4ed0; before native-02 it is 850e7f9.
Submission receipts record executable input hashes and package pins. Transport
receipts verify each retrieved compressed artifact bundle.

The candidate judge_report.md is the preserved model self-review, not execution
evidence. Docker build, Harbor execution, solver evaluation and release acceptance
have not been performed. Data staging is external to the package: use
`python stage_data.py SOURCE_DATA.csv NEW_PACKAGE_DIRECTORY` with the original
observed CSV from the experiment's SETA input manifest. The script verifies its
SHA-256 before copying into the environment and trusted verifier directories.
Do not copy tests or solution into the solver image.
