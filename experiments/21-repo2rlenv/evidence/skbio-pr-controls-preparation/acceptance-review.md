# PR2633 acceptance review

The source issue concerns numerical stability of ANCOM-BC2 mixture responsibilities when all three weighted densities underflow to zero. The native reference also handles a zero-denominator component-mean update. The exported instruction describes the former and includes a proposed fix and expected values; this is retained upstream issue content, so the task may be relatively easy.

The only F2P case is a four-sample, three-feature table. It checks three log-fold changes and three p-values against upstream-reported R ANCOMBC 2.12 values, at absolute tolerance 1e-6. This experiment has not rerun that R implementation. These inputs are a regression fixture, not established observed biological measurements. The 59 P2P tests provide broader regression protection but do not establish exhaustive numerical or scientific equivalence.

The native reward is F2P pass fraction multiplied by P2P pass fraction; strict resolution is recorded separately. With one F2P test, no partial credit is possible within the targeted regression, although P2P regressions can reduce a positive reward. Downstream Marin conversion must preserve this graded reward and its provenance. The verifier retains its native exit-code fallback for unparseable logs; acceptance must inspect per-test parsed evidence, not only the scalar score.

The environment starts from an ephemeral local image tag. The preserved baseline Dockerfile and dependency freeze support reconstruction, but this is not yet a portable released Harbor task. Initial independent controls and fresh-worker repetition now have evidence (see below); portable learner-ready rebuild and Marin execution remain pending. No blind GLM solver attempt is justified until the applicable acceptance gates are met.

Five proposed controls retain instruction, environment and all grading files exactly: unchanged code, native patch, alternative masked division for both updates, E-step-only correction, and incorrect uniform responsibilities. The E-step-only result is exploratory because it may already satisfy the reported example. These deterministic controls are not blind solver scores and are not five distinct generated tasks.

The alternative uses zero-initialized outputs with masked division for both the responsibilities and component means. This is algebraically equivalent to the native fix for finite nonnegative mixture densities: zero-sum columns already contain zero numerators; for the M-step the native fix explicitly writes zero where denominators vanish. The runtime controls will test equivalence on the retained suite; this argument does not establish behavior on all pathological floating-point inputs.

## Executed controls

The offline-profile controls and fresh-worker repeat are recorded in skbio-pr-controls-02 and skbio-pr-controls-03. Baseline and incorrect uniform responsibilities score zero; reference, equivalent masked division and E-step-only score one. A correct underflow fix with broken grouping validation scores 0.983051 (58/59 P2P, all F2P, resolved=false). All runs parse 60 tests normally. Five repeated scores match. These are limited behavioral checks, not exhaustive scientific validation or blind solver results.
