# Hierarchical Bayesian analysis of rat-tumor data: analytical grid vs MCMC posterior of (α, β)

In 71 historical rat-tumor experiments, `y_i` out of `n_i` lab rats developed endometrial stromal polyps. The analysis models these counts hierarchically (BDA3 ch. 5): `y_i | θ_i ~ Binomial(n_i, θ_i)`, with `θ_i ~ Beta(α, β)` drawn from an unknown population distribution, and a power-law hyperprior on the population parameters. You must carry out both computations in the original study and report their results.

## Input

- `inputs/rat_tumor_counts.csv` — 71 rows, columns `y` (rats developing polyps in the experiment, integer ≥ 0) and `n` (rats at risk, integer ≥ y). Each row is one experiment; keep each (y, n) pair paired.

## Part 1 — grid-based analytical marginal posterior

Using the hyperprior density `p(α, β) ∝ (α + β)^(−5/2)` and marginalizing the θ's analytically, the marginal posterior of (α, β) is, up to an additive constant,

```
log p(α, β | y) = −(5/2)·ln(α + β) + Σ_i [ lnΓ(α+β) − lnΓ(α) − lnΓ(β)
                    + lnΓ(α + y_i) + lnΓ(β + n_i − y_i) − lnΓ(α + β + n_i) ]
```

Evaluate it on a rectangular grid in transformed coordinates `x = ln(α/β)`, `z = ln(α+β)`:

- `x` takes 100 values from −2.3 to −1.31 in steps of 0.01 (i.e., −2.3, −2.29, …, −1.31; the endpoint −1.3 is excluded),
- `z` takes 400 values from 1.00 to 4.99 in steps of 0.01 (endpoint 5 excluded),

giving 100 × 400 = 40,000 grid cells. At each cell, recover `β = e^z / (e^x + 1)` and `α = e^x · β` (so α + β = e^z), convert the density to (x, z) coordinates by multiplying by the change-of-variables Jacobian factor `α · β` (equivalently, add `ln α + ln β` on the log scale), exponentiate after subtracting the grid maximum, and normalize over all 40,000 cells so the weights sum to exactly 1. The normalized weight is the posterior probability mass assigned to each cell by this discrete approximation.

From this grid, estimate the posterior means of the population parameters as the mass-weighted sums: `E[α|y] ≈ Σ_cells α · w` and `E[β|y] ≈ Σ_cells β · w`.

**Output file 1** — `outputs/analytic_posterior_grid.csv`: columns `X, Z, alpha, beta, normed_exp_trans` (in that order); one row per grid cell (40,000 data rows); `normed_exp_trans` is the normalized weight w. Row order: for each `z` ascending (1.00 → 4.99), all `x` ascending (−2.3 → −1.31). A row is identified scientifically by its (X, Z) grid coordinates; α and β are the corresponding population-parameter values at that cell. (Floating-point artifacts such as `-2.2800000000000002` from stepwise grid construction are acceptable; cell identity is the (x, z) pair.)

## Part 2 — hierarchical model fit by NUTS

Fit the same data with the study's MCMC model. Note its prior is *not* identical to Part 1's: reproduce it exactly as specified, and do not harmonize the two branches.

- `α` and `β` are independent, each with a HalfNormal prior of scale (σ) 10;
- an additional hyperprior factor `(α + β)^(−5/2)` multiplies the joint density (log-density contribution `−(5/2)·ln(α+β)`);
- `θ_i | α, β ~ Beta(α, β)`, one per experiment (i = 1 … 71);
- `y_i | θ_i ~ Binomial(n_i, θ_i)`.

Sample the joint posterior with the No-U-Turn Sampler using dual-averaging step-size adaptation targeting an average acceptance probability of 0.95, running **4 chains**, each with **2000 warmup iterations (discarded) followed by 2000 retained draws**. No random seed is prescribed. (Environment preset: PyMC 6.3.2, `pm.sample(draws=2000, tune=2000, target_accept=0.95, chains=4)` with all other arguments at their defaults, including jittered `adapt_diag` initialization.)

**Output file 2** — `outputs/pymc_ab_posterior_draws.csv`: columns `chain, draw, alpha, beta`; 8,000 data rows, one per retained draw. Chain labels are the distinct integers 1–4 and draw labels are sequential within each chain (0, 1, …, 1999 in sampling order); each row is one posterior draw of the population parameters (α and β). Draws of θ are not requested.

Estimate the posterior means of α and β as the mean of each parameter over all retained draws across all chains.

## Summary file

**Output file 3** — `outputs/posterior_mean_estimates.csv`: columns `method, parameter, estimate`; exactly 4 rows:

| method | parameter | estimate |
|---|---|---|
| `analytic_grid` | `alpha` | Part-1 estimate of E[α \| y] |
| `analytic_grid` | `beta` | Part-1 estimate of E[β \| y] |
| `pymc_mcmc` | `alpha` | Part-2 posterior-sample mean of α |
| `pymc_mcmc` | `beta` | Part-2 posterior-sample mean of β |

Report estimates at your available floating-point precision (do not round).

## Conventions

- α and β are the (dimensionless) parameters of the Beta population distribution; θ values are probabilities in [0, 1].
- `normed_exp_trans` is posterior probability mass per 0.01 × 0.01 grid cell in (x, z) space; the 40,000 weights sum to 1.
- Your MCMC results are Monte Carlo estimates: they need not match any particular seed realization bit-for-bit, but they must estimate the posterior means of the exact model specified above. Comparison tolerances for Monte Carlo error will be applied at grading.
- Missing values are not expected anywhere; if produced, they are errors.

## Environment and resources

Offline (no network). 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s runtime limit. A Python 3.13 environment with PyMC 6.3.2, NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0, ArviZ 1.3.0 is provided for convenience; any other software is acceptable provided the model, priors, and sampling configuration above are reproduced.

## Acceptance rules

## Acceptance rules (grading addendum)

The three declared output files are read exactly at the declared paths relative to the supplied output root (`analytic_posterior_grid.csv`, `pymc_ab_posterior_draws.csv`, `posterior_mean_estimates.csv`). Each file must be a CSV with exactly the specified header names in the specified order, one data row per scientific unit (40,000 grid cells; 8,000 retained draws; 4 summary rows), no extra or missing columns, no missing or non-finite values, no duplicate column names. Extra columns, appended blank lines beyond the final newline, or unparseable content count as rejections, not errors to be ignored. Missing values are errors everywhere, so NaN/inf never passes a numerical comparison.

**Grid file (`analytic_posterior_grid.csv`).** A row is identified scientifically by its (X, Z) grid coordinates; α and β are the population-parameter values at that cell. Row order is *not* a scientific target — rows may appear in any order, and cell alignment is done on (X, Z) — but coverage and multiplicity are: the 40,000 declared cells (x from −2.30 to −1.31 in 0.01 steps; z from 1.00 to 4.99 in 0.01 steps) must each appear exactly once, with no extra or out-of-range cells. X/Z values must lie on the declared 0.01 grid within 1e-6 of the exact hundredth value, so ordinary float serialization of stepwise grid artifacts (e.g. `-2.2800000000000002`, or values printed with fewer digits, e.g. `%.12g`-style or `%.6f`-rounded output) is accepted as long as the decoded coordinate matches the grid cell to within that bound. α and β must be strictly positive and are compared cell-wise against an independent deterministic recomputation of the declared Part-1 computation from the original supplied counts: |submitted − expected| ≤ 1e-9·|expected| (with a tiny absolute addend 1e-15). `normed_exp_trans` must be nonnegative, sum to 1 within 1e-9 over all 40,000 rows, and match the recomputed normalized weight per cell: |submitted − expected| ≤ 1e-8·|expected| plus a 1e-30 absolute floor (so near-zero weights are compared essentially exactly). Denominator convention: relative tolerance is with respect to the independently recomputed expected value. Faithful value promotion (parsing to float64) and ordinary native CSV serialization are accepted; a representation is not rejected merely because it prints fewer digits, but values that are rounded so far that they drift past the tolerances above fail.

**Draws file (`pymc_ab_posterior_draws.csv`).** Chain labels must be the distinct integers 1–4 and draw labels the distinct integers 0–1999 within each chain, exactly 2,000 rows per chain (8,000 total). Row identity is the draw, not its position, so rows may be reordered within those label constraints, but relabeled chains, truncated/padded chains, or duplicate-row padding are rejections. α and β draws must be strictly positive, and the 8,000 (α, β) rows must be distinct values (duplicated 4 × 2000 blocks are rejections). Because no seed is prescribed, per-draw values are not compared; instead, the submitted draws are statistically validated against the exact posterior of the *specified* Part-2 model (independent hwHalfNormal(σ = 10) priors on α and β, multiplied by the (α+β)^(−5/2) hyperprior factor, Beta θᵢ, Binomial likelihood, θ marginalized analytically), computed by deterministic numerical integration on the original counts. Acceptance limits, applied to the submitted plain arithmetic means and pooled sample standard deviations: |mean − exact mean| ≤ 2.5% of the exact mean for each of α and β (2.5% relative, denominator = the exact mean); |sd − exact sd| ≤ 20% of the exact sd; |Pearson corr(α, β) − exact corr| ≤ 0.15; and each chain's mean α (and β) within 0.50 exact posterior sd of the pooled mean. These are limits on observable output differences for the prescribed 4 × 2000 retained-draw sample size. Wrong-prior samples — in particular the Part-1 prior without the HalfNormal envelope (≈ +20% mean shift for α) — fail these limits.

**Summary file (`posterior_mean_estimates.csv`).** Exactly the 4 required (method, parameter) pairs, each once, with labels exactly `analytic_grid`/`pymc_mcmc` and `alpha`/`beta`. Each estimate must equal a deterministic function of the submitter's own other files, comparing finite float values without rounding: the `analytic_grid` rows equal the mass-weighted sums Σ(alpha·w) and Σ(beta·w) over the submitted grid columns (tolerance 1e-10 relative plus 1e-12 absolute), and the `pymc_mcmc` rows equal the plain arithmetic mean of the submitted alpha and beta draw columns (tolerance 1e-8 relative plus 1e-10 absolute). Estimates must be reported at available floating-point precision; deliberate rounding to a few decimals fails these tolerances. The deliberate prior difference between Part 1 and Part 2 is part of the task and is not normalized away by any comparison.

The grader reads the original, hash-checked task input counts (`rat_tumor_counts.csv`) from the directory named by the `BIOTASKS_TRUSTED_INPUT_DIR` environment variable; no solver-workspace copies are used and no answer values are embedded in the grader. File placement is checked exactly at the declared paths; files placed under an extra `outputs/` layer beneath the supplied output root are at the wrong paths and fail.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
