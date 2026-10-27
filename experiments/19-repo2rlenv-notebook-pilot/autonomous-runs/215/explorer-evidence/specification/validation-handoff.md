## Input derivation and provenance

- `inputs/rat_tumor_counts.csv` is a proposed materialization of the 71 (y, n) pairs embedded verbatim in `inputs/original.py` (call sites 76–89; data lineage BDA3 3rd ed. p. 102; notebook MIT-licensed). Source order preserved. **Not yet built**: construction must create it exactly (integers, no header quotes issues), hash-pin it, and verify 71 rows and y_i ≤ n_i for all rows. Note the open redistribution review for derived inputs in provenance.json before publication.
- The likelihood sums over experiments, so it is invariant to row permutation; only within-row (y, n) pairing matters. The file is supplied in source order.

## Endpoint lineage

1. `outputs/analytic_posterior_grid.csv` ↔ recorded reference `rat_tumor_analytic_posterior_grid.csv` (sha256 14cbefc7a942cdc407be6118ec341fb8914dd96b56a99b8545ca5382743010e4, 3,871,960 bytes; output-audit: 40,000 rows, columns X/Z/alpha/beta/normed_exp_trans, X 100 distinct −2.3…−1.31, Z 400 distinct 1.00…4.99, row order z-outer/x-inner). Deterministic: byte-identical across both recorded reference replays. Column schema is an exact matching of the reference export; the reference is a fair ground truth without new computation.
2. Analytic mean estimates ↔ unnamed source expressions (lines 175–178): `(df.alpha * df.normed_exp_trans).sum()` and `(df.beta * df.normed_exp_trans).sum()`, displayed rounded to 3 decimals in the notebook. Exactly recoverable as projections of the reference grid; no rerun needed.
3. `outputs/pymc_ab_posterior_draws.csv` ↔ variable `ab` (dims chain/draw/param, values [alpha, beta]) of recorded reference `rat_tumor_pymc_posterior_samples.nc` (sha256 2cfbb266d21ce2a5c2dde4ed2a36e2a348a7a6b61ac096993ee326c4e3df3fc7; also contains X, Z, theta, which are NOT required outputs — see exclusion ledger in review). The .nc is serialized via the netcdf4 engine after a preparation h5py repair; storage detail only.
4. MCMC mean estimates ↔ unnamed source expression (line 223): `trace.posterior["ab"].mean(("chain","draw"))` — mean over 4 chains × 2,000 retained draws = 8,000 draws.

## Scientific meaning and identity constraints

- Grid cell identity = (x, z) coordinate pair, NOT row position or serialized float string; source coordinates contain artifacts such as "-2.2800000000000002" from `np.arange`. Validation should match cells by coordinates within a small tolerance (or verify the solver's ordering convention matches the specified z-outer/x-inner layout); the required scientific invariants are α+β = e^z at every cell and Σ normed_exp_trans = 1 over 40,000 cells. `normed_exp_trans` is probability mass per 0.01×0.01 cell, not density.
- MCMC draws: per-draw values are **not** reproducible (source sets no seed; recorded replays yield different .nc hashes — fe6d7b…, f147c1… vs baseline 2cfbb2… — and scalar-mean drift was NOT measured). The scientific identity is the joint posterior distribution of (α, β) under the exact model below; chain/draw labels are arbitrary bookkeeping and must not be treated as an answer key. Draw ordering across chains is not meaningful.
- The two branches use different priors by design: analytic branch has only (α+β)^(−5/2); MCMC branch multiplies independent HalfNormal(σ=10) priors on α and β by the same power-law potential. Ground-truth each branch against its own model; do not accept cross-branch matching as the grading rule (the notebook calls them only "encouragingly close").

## Executed methodology facts (measured evidence)

- Reference execution: PyMC 6.3.2, NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0, ArviZ 1.3.0, xarray 2026.9.0 (full version list: trial/environment.txt; uv.lock retained, sha 907423dc…). NUTS ("Initializing NUTS using jitter+adapt_diag… Multiprocess sampling (4 chains in 4 jobs)"), ~4 s sampling, whole reference run ~12 s, exit 0.
- `pm.sample` explicit arguments: draws=2000, tune=2000, target_accept=0.95; everything else at defaults — chains resolved to 4 in the 4-CPU sandbox. The task pins 4 chains so the solver configuration is explicit; this is a documented resolution of a default, and expected effect is only on Monte Carlo error, not the target quantity.
- HalfNormal sigma=10 is explicit in source (line 200); the potential is exact (−5/2)·log(sum(ab)) (line 194), not a normalized distribution.

## Unresolved questions and validation obligations

1. **MC-error magnitude of the MCMC mean estimates is unmeasured.** Two replays exist but only byte hashes of the .nc were compared; mean-level drift across runs was not quantified. Validation must measure legitimate variation (repeated reference runs, or numerical integration of the exact model posterior mean under HalfNormal(10) × (α+β)^(−5/2) × likelihood) before setting tolerances; no tolerance is asserted here.
2. Cross-platform/implementation float agreement of the analytic grid and means (gammaln differences, last-bit variation in arange coordinates) — calibrate numerically; recommend coordinate-tolerance-based cell matching rather than string equality.
3. Rounding: source displays analytic means rounded to 3 decimals; the task requests unrounded values. Decide the accepted precision at validation.
4. Chain/draw label conventions (integers 1–4 vs 0–3, draw indices): treat as arbitrary identifiers; accept any consistent labeling if it does not alias distinct draws.
5. Whether an alternative sampler stack (e.g., Stan/cmdstanpy with adapt_delta=0.95, 4 chains, 2000/2000) lands within the same MC tolerances — a portability question only executable validation can answer.
6. Construction obligation: materialize and hash-pin `inputs/rat_tumor_counts.csv`; verify 71 rows, pairing, and values against the embedded arrays before solver dispatch. Distribution review for the derived input remains open.

## Exclusions recap (see review for full ledger)

Posterior-mode annotation (plot block; subsumed by argmax projection of the required grid), arviz diagnostic plots, theta draws (no source consumer), X/Z draws (pointwise transforms of ab, diagnostic-only) — all excluded on source evidence, recorded for the coverage audit. The reference .nc and grid CSV are private evidence; neither is supplied to the solver.
