## Scope assessment

The notebook (original.py, sha 1163731…) contains two append-only terminal exports after conversion: the analytic marginal posterior grid (analytic_marginal_posterior_grid.csv) and the PyMC posterior draws of the hyperparameters (pymc_posterior_ab.csv). Both are recorded outputs of an executed reference run under the pinned stack. The `source_operations` inventory matches the full original source; the reference script (trial/reference.py, diff empty) reproduces the original line-for-line.

## Measured factual basis

Reference artifact identities (verified by the execution stage and hash-pinned in `reference_inspection`):

- analytic_marginal_posterior_grid.csv — sha256 `14cbefc7a942…`, 3871960 bytes.
- pymc_posterior_ab.csv — sha256 `bbc9837764f4…`, 488015 bytes.

Output schema (from the structural audit and my read-only inspection of these exact files):
- analytic_marginal_posterior_grid.csv: columns X,Z,alpha,beta,normed_exp_trans; 40000 rows (+1 header) = 100 distinct grid-axis values × 400 unique grid values; confirmed enumerated grid lines exactly atached, e.g. lines 2-6 with X = -2.29, -2.280…, -2.270…, -2.260… and Z = 1.0 constant, confirming the original np.meshgrid grid ordering (X-major, Z-minor) was serialized.
- pymc_posterior_ab.csv: columns chain,draw,param,ab; 16000 rows (+1 header) = 4 chains × 2000 draws × 2 params (alpha/beta) per (chain,draw) pair. Head rows confirm chain-major/draw-with-param-nested ordering (chain 0, draw 0, param alpha followed by param beta; chain 0, draw 1 next, etc.).

Execution observations (trial/result.json, task 1, test 1): pm.sample completed in ~5s of sampling under the pinned stack, exit 0, both artifacts produced, satisfying the plan's concern about 600s CPU budget. This is recorded evidence from execution, not a robustness guarantee I independently re-ran.

Repeatability observations (repeatability_observations): analytic grid is byte-identical across accessible runs. The MCMC export is not (different draws each run, row multinomial even differs), as expected without a seed — the original source does not seed pm.sample. This is a scientific property of the analysis, not a defect.

## Repeatability / repair status

- No repair was needed: `source.diff` is empty, and reference.py matches the original source exactly.
- Replays of the reference produce byte-identical output for the analytic grid; MCMC draws differ run-to-run as expected. Neither "passing reference and structural audit, plus the supplied finite replay observations" nor any replay analysis establishes a grading tolerance.

## Open verification issues blocking immediate `draft_ready`

1. **Chain membership/structure of the MCMC export beyond rows 1-5.** I inspected only head rows (the read window I chose). The audit says 4 distinct chain values, 2000 distinct draw values, 16000 rows, but this does not establish whether every (chain, draw) pair appears with exactly 2 param rows and no additional sampling states, divergences, or stray extra chains encoded, nor the row-shape for chains 1-3 (e.g., whether "chain"-per-chain multiprocess sampling indicó the same 2-param structure). I did not re-examine the multi-value behavior of the number of chains parameter or whether pm.sample's counter "multiprocess sampling (4 chains in 4 jobs)" at this version is issued with 4 actual chains across 16000 rows in this export (the audit indicates it is). A tail/chain-boundary read or an equivalent structural assertion is needed to lock the row schema of this CSV before a solver-facing comparison rule is drafted.
2. **Grid boundary/precision identity.** The audit reports distinct X values = 100 and distinct Z = 400, but does not confirm that the serialized X values are strictly the output of `np.arange(-2.3, -1.3, 0.01)` and Z of `np.arange(1, 5, 0.01)` (count 100 vs 400) rather than a permutation, spacing drift, or truncated endpoint (float arange endpoints should be `arange(-2.3, …, 0.01)` yielding 100 values, max observed `-1.310000000000021`, consistent with exclusive stop). Observed head rows are consistent with this but not dispositive of the full axis. Confirming that the X/Z columns are each monotonically increasing within their cycle and that the (X,Z) grid is the complete Cartesian product (each X seen with each Z) locks the alignment of p(x,z|y) to grid coordinates for a future comparator.
3. **Scientific identity of `normed_exp_trans` vs a "density" claim.** The notebook states "This will ensure the density is normalized" and computes `exp_trans / sum(exp_trans)`. This is a discrete probability mass function over grid cells, not a continuous per-unit-area density; a correct comparator must compare mass (dimensionless, sums to 1) rather than density per unit (x,z)-area, or, if density is preferred, multiply by the 0.01×0.01 cell area. This is a representation choice that changes the requested quantity and must be pinned in the task brief (I will specify "discrete posterior mass over the grid, summing to 1", the original's convention), but the validation stage must confirm the reference values actually sum to 1.0 (audit states sum 1.0 in the setup-stage spot check; not independently re-verified from the artifact bytes).
4. **MCMC-branch fidelity checks relied on the audit, not a re-run.** The audit reports the executed sampling completed for the declared draws (2000 per chain, 4 chains, target_accept=0.95, HalfNormal(10) hyperprior with logp_ab potential) and exported `trace.posterior["ab"]`. I have not independently re-executed the model to confirm a modern, mature posterior summary (mean alpha, mean beta matching analytic basin) — the audit's own "ArviZ posterior-mean estimates converge to the analytic values within Monte Carlo error" is listed as an unresolved assumption, not a verified fact. This is a property of the analysis, not a defect of the reference; it does not block the task definition but must remain an explicit validation question for the grader stage, not a public requirement.

## Exclusions consistent with target

The grid and draw exports fully cover the analysis's two scientific endpoints (analytic marginal posterior; MCMC hyperparameter posterior). Diagnostic plots (az.plot_rank_dist, plot_pair, plot_dist, contourf heatmap, mode marker) are visualization outputs whose underlying numerical content is fully contained in the two exported tables; excluded as endpoints under the endpoint rule, with numeric content preserved in exports. The unnamed expressions `(df.alpha * df.normed_exp_trans).sum().round(3)` and the same for beta are precisely recoverable from the grid export (weighted sum using the exported mass column), so they are not lost. The original narrative's posterior-mode marker (X[0, ix_x], Z[ix_z, 0]) is recoverable from the argmax of the exported density surface; likewise not lost. No intervention below top-level required, so no source fidelity concerns about custom repair.

## Coverage ledger (source operations)

All 68 literal call sites in `source_operations` are assigned: data literals and meshgrid construction, log-likelihood/log-prior transforms, DataFrame grid construction, density normalization, plot rendering (excluded as visualization, retained numerically in exports), analytic posterior-mean expressions (recoverable from export), PyMC model construction and sampling, ArviZ diagnostic plots (excluded), posterior-mean expression (recoverable from export), export code. No unnamed branch was identified as a missing scientific endpoint.

## Disposition rationale

The task is scientifically well-defined and its two endpoints are recorded and hash-pinned. However, the four open verification issues above — particularly the MCMC row-shape/chain-structure identity and the grid-geometry monotonicity — are needed to pin the output schema identity doors of the public question and its future comparator. Under policy, missing facts that define the reference (not merely tolerance calibration) should surface as `needs_evidence` until inspected.

## Proposed task shape (for once evidence completes)

Two requested outputs with schemas mirroring the existing reference exports:
1. analytic_marginal_posterior_grid.csv — the normalized discrete posterior mass p(x,z|y) over the complete (log(alpha/beta), log(alpha+beta)) grid with columns X,Z,alpha,beta,normed_exp_trans.
2. pymc_posterior_ab.csv — posterior draws of (alpha,beta) with columns chain,draw,param,ab.

Withheld answers include posterior means of alpha and beta (analytic and MCMC), posterior mode/mode-region, and any derived summaries. Downstream scientific work retained: computing the analytic marginal posterior mass itself (grid evaluation, log-likelihood with gammaln, hyperprior, Jacobian, normalization), building/sampling the hierarchical model, and exporting draws in the named schema. Provenance-bearing intermediates are appropriate if needed to stabilize a comparison (e.g., pinning sample v. identity of draws input to summary computation), but no such input is required by the current formulation.
