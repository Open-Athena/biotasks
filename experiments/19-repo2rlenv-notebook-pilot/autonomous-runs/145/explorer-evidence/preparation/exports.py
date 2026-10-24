import os

_export_out_dir = "/work/outputs"
os.makedirs(_export_out_dir, exist_ok=True)

# Endpoint 1: analytic marginal posterior density on the (X, Z) grid.
# `df` holds the grid identifiers (X, Z), the back-transformed alpha/beta,
# and the normalized posterior weight normed_exp_trans produced by the source.
analytic_posterior_grid = df[["X", "Z", "alpha", "beta", "normed_exp_trans"]]
analytic_posterior_grid.to_csv(
    os.path.join(_export_out_dir, "analytic_marginal_posterior_grid.csv"),
    index=False,
)

# Endpoint 2: PyMC posterior samples for the hyperparameters (ab) and their
# log-scale transforms (X, Z) from the existing `trace` InferenceData.
trace.posterior[["ab", "X", "Z"]].to_netcdf(
    os.path.join(_export_out_dir, "pymc_posterior_ab_X_Z.nc")
)