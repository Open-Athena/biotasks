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

**Output file 1** — `outputs/analytic_posterior_grid.csv`: columns `X, Z, alpha, beta, normed_exp_trans` (in that order); one row per grid cell (40,000 data rows); `normed_exp_trans` is the normalized weight w. Row order: for each `z` ascending (1.00 → 4.99), all `x` ascending (−2.3 → −1.31). A row is identified scientifically by its (X, Z) grid coordinates; α and β are the corresponding population-parameter values at that cell.

## Part 2 — hierarchical model fit by NUTS

Fit the same data with the study's MCMC model. Note its prior is *not* identical to Part 1's: reproduce it exactly as specified, and do not harmonize the two branches.

- `α` and `β` are independent, each with a HalfNormal prior of scale (σ) 10;
- an additional hyperprior factor `(α + β)^(−5/2)` multiplies the joint density (log-density contribution `−(5/2)·ln(α+β)`);
- `θ_i | α, β ~ Beta(α, β)`, one per experiment (i = 1 … 71);
- `y_i | θ_i ~ Binomial(n_i, θ_i)`.

Sample the joint posterior with the No-U-Turn Sampler using dual-averaging step-size adaptation targeting an average acceptance probability of 0.95, running **4 chains**, each with **2000 warmup iterations (discarded) followed by 2000 retained draws**. No random seed is prescribed. (Reference preset: PyMC 6.3.2, `pm.sample(draws=2000, tune=2000, target_accept=0.95)` with all other arguments at their defaults, including jittered `adapt_diag` initialization.)

**Output file 2** — `outputs/pymc_ab_posterior_draws.csv`: columns `chain, draw, alpha, beta`; 8,000 data rows, one per retained draw. Chain labels are arbitrary distinct integers 1–4 and draw labels are sequential within each chain; each row is one posterior draw of the population parameters (α and β). Draws of θ are not requested.

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
