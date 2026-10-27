# --- Export: terminal scientific results (appended by preparation stage) ---
import os as _export_os

_export_out_dir = "/work/outputs"
_export_os.makedirs(_export_out_dir, exist_ok=True)

# Endpoint 1: analytical marginal posterior of (alpha, beta) on the
# (log(alpha/beta), log(alpha+beta)) grid, normalized to a probability mass.
# Export only the endpoint fields and grid identifiers; the intermediate
# log_posterior / log_jacobian / transformed / exp_trans columns are omitted.
df[["X", "Z", "alpha", "beta", "normed_exp_trans"]].to_csv(
    _export_os.path.join(_export_out_dir, "rat_tumor_analytic_posterior_grid.csv"),
    index=False,
)

# Endpoint 2: PyMC posterior samples (ab, X, Z, theta) of the hierarchical
# rat-tumor model, saved with the posterior group's own native writer.
trace.posterior.to_netcdf(
    _export_os.path.join(_export_out_dir, "rat_tumor_pymc_posterior_samples.nc")
)