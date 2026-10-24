#!/usr/bin/env python3
"""Solve the rat-tumor hierarchical Bayes task from the supplied inputs only.

Part 1 reproduces the analytic collapsed beta-binomial marginal posterior of
(alpha, beta) on the (x, z) grid exactly as specified in the public task.
Part 2 fits the hierarchical model with the half-normal + (a+b)^(-5/2)
hyperprior using PyMC NUTS and reports pooled posterior means.
Only inputs/ (the counts CSV) is read; no reference material is accessed.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from scipy.special import gammaln


def log_likelihood(alpha, beta, y, n):
    """Collapsed beta-binomial log-likelihood, summed over experiments."""
    LL = 0
    for Y, N in zip(y, n):
        LL += (
            gammaln(alpha + beta)
            - gammaln(alpha)
            - gammaln(beta)
            + gammaln(alpha + Y)
            + gammaln(beta + N - Y)
            - gammaln(alpha + beta + N)
        )
    return LL


def solve_part1(y, n, output_dir):
    # Half-open grid, exactly as specified: 100 x-values, 400 z-values.
    X, Z = np.meshgrid(np.arange(-2.3, -1.3, 0.01), np.arange(1, 5, 0.01))
    flat_x = X.ravel()
    flat_z = Z.ravel()

    # (x, z) -> (alpha, beta) back-transform.
    beta_v = np.exp(flat_z) / (np.exp(flat_x) + 1.0)
    alpha_v = np.exp(flat_x) * beta_v

    log_prior = -5.0 / 2.0 * np.log(alpha_v + beta_v)
    log_posterior = log_prior + log_likelihood(alpha_v, beta_v, y, n)
    log_jacobian = np.log(alpha_v) + np.log(beta_v)
    transformed = log_posterior + log_jacobian

    exp_trans = np.exp(transformed - transformed.max())
    normed = exp_trans / exp_trans.sum()

    out = pd.DataFrame(
        {
            "X": flat_x,
            "Z": flat_z,
            "alpha": alpha_v,
            "beta": beta_v,
            "normed_exp_trans": normed,
        }
    )
    out.to_csv(
        os.path.join(output_dir, "analytic_marginal_posterior_grid.csv"),
        index=False,
    )

    mean_alpha = float((out["alpha"] * out["normed_exp_trans"]).sum())
    mean_beta = float((out["beta"] * out["normed_exp_trans"]).sum())

    idx_mode = int(normed.argmax())
    mode_x = float(out["X"].iloc[idx_mode])
    mode_z = float(out["Z"].iloc[idx_mode])

    summary = {
        "mean_alpha": mean_alpha,
        "mean_beta": mean_beta,
        "mode_x": mode_x,
        "mode_z": mode_z,
    }
    with open(os.path.join(output_dir, "analytic_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)


def solve_part2(y, n, output_dir):
    import pymc as pm
    import pytensor.tensor as pt

    coords = {
        "obs_id": np.arange(len(n)),
        "param": ["alpha", "beta"],
    }

    def logp_ab(value):
        """(a + b)^(-5/2) prior factor."""
        return pt.log(pt.pow(pt.sum(value), -5 / 2))

    with pm.Model(coords=coords) as model:
        n_val = pm.Data("n_val", n)
        ab = pm.HalfNormal("ab", sigma=10, dims="param")
        pm.Potential("p(a, b)", logp_ab(ab))
        theta = pm.Beta("theta", alpha=ab[0], beta=ab[1], dims="obs_id")
        pm.Binomial("y", p=theta, observed=y, n=n_val)
        trace = pm.sample(
            draws=2000,
            tune=2000,
            target_accept=0.95,
            chains=2,
        )

    pooled = trace.posterior["ab"].mean(("chain", "draw"))
    param_names = [str(v) for v in pooled["param"].values]
    pooled_vals = [float(v) for v in pooled.values]
    m = dict(zip(param_names, pooled_vals))

    result = {
        "mean_alpha": m["alpha"],
        "mean_beta": m["beta"],
        "n_chains": 2,
        "draws_per_chain": 2000,
        "target_accept": 0.95,
        "sampler": "PyMC NUTS (pymc %s)" % pm.__version__,
    }
    with open(os.path.join(output_dir, "mcmc_posterior_means.json"), "w") as fh:
        json.dump(result, fh, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    data = pd.read_csv(os.path.join(args.input_dir, "rat_tumor_counts.csv"))
    y = data["y"].to_numpy()
    n = data["n"].to_numpy()
    if len(y) != len(n):
        raise SystemExit("y and n columns must have equal length")
    if not np.all((y >= 0) & (y <= n)):
        raise SystemExit("input violates 0 <= y <= n")

    solve_part1(y, n, args.output_dir)
    solve_part2(y, n, args.output_dir)


if __name__ == "__main__":
    main()

