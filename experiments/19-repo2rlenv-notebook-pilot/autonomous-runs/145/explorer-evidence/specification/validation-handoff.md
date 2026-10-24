# Validation handoff (private)

## 1. Input materialization (construction, not yet built/validated)

- Create `rat_tumor_counts.csv` from the arrays embedded verbatim in `inputs/original.py` (lines 76–95; two 71-element integer arrays `y`, `n`, BDA3 p. 102 data, lineage recorded in provenance.json). One row per experiment, columns `y,n`, row order identical to the source arrays. Register its sha256. MIT-licensed notebook; the counts are published BDA3 table data — **provenance.json flags that derived materialized inputs still need a separate redistribution review before publication; complete this before release.**
- No other inputs are needed anywhere in the task.

## 2. Private reference answers (from existing recorded artifacts; no methodological change)

- Analytic branch: `analytic_marginal_posterior_grid.csv` (sha256 14cbefc7…, 40,000 rows) is recorded and replay-byte-identical. Construction should privately compute `mean_alpha = Σ α·w`, `mean_beta = Σ β·w`, and the argmax cell from this artifact (provenance: derived from recorded reference export, zero recomputation of science), and record them as the reference answers. Reference values from the notebook's display expressions ((df.alpha*normed).sum().round(3), etc.) can be independently cross-checked against narrative expectations but must not be copied into the public brief.
- MCMC branch: pooled `ab` posterior mean is computable from the recorded `pymc_posterior_ab_X_Z.nc` (sha256 c891d561…); compute and register privately. Note the recorded sample is one stochastic realization — see tolerance calibration below.

## 3. Proposed comparison rules (to validate; no numeric tolerances are established yet)

- **Output 1 grid:** match rows by (X, Z) key. Proposed matching: nearest-coordinate matching within a small absolute coordinate tolerance (numpy `arange` values are `start + i*step`; other stacks using the same arithmetic should agree bit-for-bit, but R `seq` accumulation paths must be measured — this is an unresolved measurement). Value comparison kind: relative error for `alpha`, `beta`; for `normed_exp_trans` a hybrid absolute+relative rule because weights span ~4.5e-19 to ~4.4e-4. Calibrate all tolerances by cross-implementation recomputation (e.g., Python/scipy vs R/mpmath vs a second independent code path) before use; require a row-permutation probe to confirm order-independence of the grader.
- **Output 2:** `mean_alpha`/`mean_beta` compared numerically (kind: relative; tolerance calibrated from the same cross-implementation measurements). `mode_x`/`mode_z`: exact grid-coordinate match after keying; grader must also check consistency with the solver's own Output 1 argmax. **Unresolved:** measure the margin between the top two grid weights to confirm the mode cell is unique and robust to summation-order noise; if the gap is not comfortably above numerical variation, DROP the mode endpoint (keeping means), do not invent a tie-break rule.
- **Output 3:** stochastic result. Calibrate by (a) running the Part 2 reference configuration repeatedly with fresh seeds and measuring the spread of pooled `ab` means (est. 2 chains × 2000 draws, target_accept 0.95); (b) running counterfactual variants to measure separation: drop the Potential (pure half-normal prior), drop the half-normal factor (part-1 prior alone), and an uncollapsed/likelihood error. Set the acceptance tolerance strictly above measured MC spread but below the smallest variant separation; verify the two are well separated, otherwise escalate rather than widen. The tolerance must be published to the solver before finalization. A single reference run does NOT establish these values.

## 4. Measured facts vs assumptions

Measured/executed: reference ran to completion offline in ~15 s (limit 600 s), peak RSS ~360 MiB; NUTS init `jitter+adapt_diag`, 2 chains × 2000 tune + 2000 draws, target_accept 0.95 (execution log in trial/result.json); grid is deterministically byte-identical across 3 runs; netCDF is byte-different in every replay (grades must never hash- or draw-compare it).

Approved scope: terminal display-expression means and the contour-annotated mode were excluded from exports by plan.json but are preserved as required solver outputs (faithful recomputation path, policy-approved); no endpoint dropped.

Unvalidated assumptions needing executable validation: all numeric tolerances above; mode uniqueness; CSV input materialization; whether cross-stack grid coordinates match within the proposed matching tolerance; MCMC tolerance/variant separation.

## 5. Additional validation probes for wrong-answer detection

Grid/means: omitting the log-Jacobian (ln α + ln β); skipping the max-subtraction (underflow to zero weights); inclusive-endpoint grid (101×401); sign error in −5/2; summing weights over only one axis. Part 2: variants in §3(b); fewer chains/draws than specified. Run these to confirm the grader separates them from correct answers.
