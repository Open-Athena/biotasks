import argparse
import os

import numpy as np
import pandas as pd
from scipy.special import gammaln


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    counts = pd.read_csv(os.path.join(args.input_dir, "rat_tumor_counts.csv"))
    y = counts["y"].to_numpy()
    n = counts["n"].to_numpy()
    N = len(n)

    # ------------------------------------------------------------------
    # Part 1: analytical marginal posterior on the (x, z) grid.
    # ------------------------------------------------------------------
    X, Z = np.meshgrid(np.arange(-2.3, -1.3, 0.01), np.arange(1, 5, 0.01))
    df = pd.DataFrame(np.c_[X.ravel(), Z.ravel()], columns=["X", "Z"])

    def trans_to_beta(x, z):
        return np.exp(z) / (np.exp(x) + 1)

    def trans_to_alpha(x, z):
        return np.exp(x) * trans_to_beta(x, z)

    df["alpha"] = trans_to_alpha(df.X, df.Z)
    df["beta"] = trans_to_beta(df.X, df.Z)

    alpha = df["alpha"].to_numpy()
    beta = df["beta"].to_numpy()

    # Beta-binomial marginal log-likelihood, summed over the 71 experiments
    # in supplied row order (the sum is order-invariant).
    LL = np.zeros(alpha.shape)
    for Y_i, N_i in zip(y, n):
        LL += (
            gammaln(alpha + beta)
            - gammaln(alpha)
            - gammaln(beta)
            + gammaln(alpha + Y_i)
            + gammaln(beta + N_i - Y_i)
            - gammaln(alpha + beta + N_i)
        )

    log_posterior = -5.0 / 2 * np.log(alpha + beta) + LL
    log_jacobian = np.log(alpha) + np.log(beta)
    transformed = log_posterior + log_jacobian
    exp_trans = np.exp(transformed - transformed.max())
    normed = exp_trans / exp_trans.sum()

    df["normed_exp_trans"] = normed

    alpha_grid_mean = float((df["alpha"] * df["normed_exp_trans"]).sum())
    beta_grid_mean = float((df["beta"] * df["normed_exp_trans"]).sum())

    df[["X", "Z", "alpha", "beta", "normed_exp_trans"]].to_csv(
        os.path.join(args.output_dir, "analytic_posterior_grid.csv"), index=False
    )

    # ------------------------------------------------------------------
    # Part 2: hierarchical model fit by NUTS (PyMC).
    # ------------------------------------------------------------------
    import pymc as pm
    import pytensor.tensor as pt

    coords = {
        "obs_id": np.arange(N),
        "param": ["alpha", "beta"],
    }

    def logp_ab(value):
        """(alpha + beta)^(-5/2) hyperprior factor, on the log scale."""
        return pt.log(pt.pow(pt.sum(value), -5 / 2))

    with pm.Model(coords=coords) as model:
        n_val = pm.Data("n_val", n)
        ab = pm.HalfNormal("ab", sigma=10, dims="param")
        pm.Potential("p(a, b)", logp_ab(ab))

        theta = pm.Beta("theta", alpha=ab[0], beta=ab[1], dims="obs_id")
        p = pm.Binomial("y", p=theta, observed=y, n=n_val)

        trace = pm.sample(
            draws=2000, tune=2000, target_accept=0.95, chains=4
        )

    ab_post = trace.posterior["ab"]
    param_names = [str(v) for v in ab_post.coords["param"].values]
    ia = param_names.index("alpha")
    ib = param_names.index("beta")
    vals = ab_post.transpose("chain", "draw", "param").values
    n_chain, n_draw, _ = vals.shape

    rows = [
        (c + 1, d, float(vals[c, d, ia]), float(vals[c, d, ib]))
        for c in range(n_chain)
        for d in range(n_draw)
    ]
    draws_df = pd.DataFrame(rows, columns=["chain", "draw", "alpha", "beta"])
    draws_df.to_csv(
        os.path.join(args.output_dir, "pymc_ab_posterior_draws.csv"),
        index=False,
    )

    alpha_mc_mean = float(vals[..., ia].mean())
    beta_mc_mean = float(vals[..., ib].mean())

    summary = pd.DataFrame(
        {
            "method": ["analytic_grid", "analytic_grid", "pymc_mcmc", "pymc_mcmc"],
            "parameter": ["alpha", "beta", "alpha", "beta"],
            "estimate": [alpha_grid_mean, beta_grid_mean, alpha_mc_mean, beta_mc_mean],
        }
    )
    summary.to_csv(
        os.path.join(args.output_dir, "posterior_mean_estimates.csv"), index=False
    )


if __name__ == "__main__":
    main()

