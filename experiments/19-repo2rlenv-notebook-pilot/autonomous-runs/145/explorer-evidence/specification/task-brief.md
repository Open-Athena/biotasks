# Hierarchical Bayesian inference for 71 historical rat-tumor experiments

## Supplied input

- `rat_tumor_counts.csv` — one row per historical experiment, columns `y`, `n`:
  - `y`: number of lab rats that developed endometrial stromal polyps in that experiment;
  - `n`: number of rats at risk in that experiment.
- Use **all rows exactly as supplied**; there is no filtering. The likelihood is exchangeable over experiments, but preserve the supplied row order in any per-experiment reporting. These are historical observed counts (Bayesian Data Analysis 3rd ed., ch. 5, p. 102 data), not simulated data.

The task has two independent parts. **The two parts use different hyperpriors on (α, β); they are different scientific quantities and must both be reported separately.**

## Part 1 — Analytic marginal posterior of (α, β) on a grid

Model: for experiment *i*, `y_i ~ Binomial(n_i, θ_i)` and `θ_i ~ Beta(α, β)`, with hyperprior density `p(α, β) ∝ (α + β)^(−5/2)` for α, β > 0 (improper; the posterior is proper for these data). Marginalize the θ_i analytically (beta–binomial collapse) to obtain the marginal posterior of (α, β).

Work in the reparameterization `x = ln(α/β)`, `z = ln(α + β)`:

- Grid: `x` takes the values −2.30, −2.29, −2.28, … in steps of 0.01, **strictly less than −1.30** (100 values, last is −1.31); `z` takes the values 1.00, 1.01, … in steps of 0.01, **strictly less than 5.00** (400 values, last is 4.99). Use all 100 × 400 = 40,000 combinations (half-open grid semantics: the stop endpoints −1.30 and 5.00 are excluded).
- Per cell: `α = e^(x+z) / (1 + e^x)` and `β = e^z / (1 + e^x)`.
- Per cell log-weight (compute in log space throughout):

  ℓ(x, z) = −(5/2)·ln(α + β)
  + Σ_i [ ln Γ(α + β) + ln Γ(α + y_i) + ln Γ(β + n_i − y_i) − ln Γ(α) − ln Γ(β) − ln Γ(α + β + n_i) ]
  + ln α + ln β   (log-Jacobian of the (α, β) → (x, z) change of variables)

- Normalize numerically stably: subtract the maximum log-weight over the whole grid before exponentiating, then divide by the sum over all 40,000 cells, giving grid weights `w(x, z)` that sum to 1.

### Output 1: `analytic_marginal_posterior_grid.csv`

CSV with header (in this column order): `X,Z,alpha,beta,normed_exp_trans`. One row per grid cell; any row order is acceptable (the grader matches rows by their (X, Z) coordinates), but every cell must appear exactly once. At least 10 significant digits of precision; no missing or non-finite values. `alpha`/`beta` must be the (X, Z) values transformed back as defined above, and `normed_exp_trans` the normalized weight `w`.

### Output 2: `analytic_summary.json`

JSON object with exactly these keys:
- `mean_alpha`: E[α | y] estimated as Σ_cells α·w (the posterior mean of α under this grid).
- `mean_beta`: E[β | y] estimated as Σ_cells β·w.
- `mode_x`, `mode_z`: the `x` and `z` grid values of the single cell whose normalized weight `w` is maximal (i.e. the location of the posterior mode on this grid); these must be exactly grid coordinate values from your Output 1.

## Part 2 — Posterior means of the hyperparameters from MCMC (different prior!)

Fit the same hierarchical likelihood but with this joint prior density on the hyperparameters (a = α, b = β > 0):

  p(a, b) ∝ [half-normal(σ = 10) density in a] × [half-normal(σ = 10) density in b] × (a + b)^(−5/2)

with `θ_i ~ Beta(a, b)` and `y_i ~ Binomial(n_i, θ_i)`. **This additional half-normal factor is part of the model definition; do not replace it with the Part 1 hyperprior alone** — the two hyperpriors are intentionally different and yield different posteriors.

Sample the posterior with a gradient-based HMC/NUTS sampler configured as follows: exactly **2 chains**, each with **2000 warmup (tuning) iterations that are discarded**, **2000 retained draws per chain** (4000 pooled draws total), and step-size/dual-averaging adaptation targeting a mean acceptance statistic of **0.95**. Report the pooled posterior means of `a` and `b` (averaged over both chains and all retained draws).

### Output 3: `mcmc_posterior_means.json`

JSON object with exactly these keys:
- `mean_alpha`, `mean_beta`: pooled posterior means of a and b (floats).
- `n_chains`: 2; `draws_per_chain`: 2000 (retained); `target_accept`: 0.95.
- `sampler`: free-text name of the sampler/software used.

## Comparison and validation notes (provisional)

- Output 1 is compared cell-by-cell after matching rows by (X, Z); output precision is required to be high enough (≥ 10 significant digits) that formatting does not limit the comparison.
- Deterministic quantities (Part 1 and Output 2's statistics) are graded with tolerances that accommodate ordinary cross-library floating-point variation in log-gamma evaluations and summation order, calibrated by the grader.
- Part 2 posterior means are graded with a tolerance that reflects the Monte Carlo error of the specified sampling configuration; a properly converged, correctly specified run will pass, while a run with the wrong prior (e.g. dropping the half-normal factor or the (a+b)^(−5/2) factor) or wrong likelihood will not.
- Software choice is open: any statistics environment that implements the models above is acceptable. A pinned reference environment (PyMC 6.3.2 / NumPy 2.5.4 / SciPy 1.18.1, Python 3.13) can be provided for convenience, but is not required.

## Resource limits

Execution is fully offline (no network), with a wall-clock limit of 600 s, 4 CPU cores and 8 GiB memory.
