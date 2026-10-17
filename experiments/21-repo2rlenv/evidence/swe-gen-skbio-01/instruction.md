`ancombc2` in `skbio.stats.composition` crashes with `ValueError: Quantiles must be in the range [0, 1]` when the sampling-bias EM step encounters features whose coefficient variances are extremely small.

Minimal reproducer:

```python
import pandas as pd
from skbio.stats.composition import ancombc2

X = pd.DataFrame(
    [[154, 188, 68], [143, 63, 177], [30, 154, 96], [131, 167, 150]],
    index=list("abcd"), columns=["f0", "f1", "f2"],
)
md = pd.DataFrame({"g": pd.Categorical(["a", "a", "b", "b"])}, index=list("abcd"))
ancombc2(X, md, "g", p_adjust=None)
```

This currently emits `RuntimeWarning: invalid value encountered in divide`, originating from the responsibility normalization in `_estimate_bias_em` (`resp /= np.sum(resp, axis=0, keepdims=True)`), and then raises `ValueError: Quantiles must be in the range [0, 1]` from the quantile computation in `_estimate_bias_var`.

Root cause: the E-step of `_estimate_bias_em` evaluates three weighted Gaussian densities (for the zero, negative, and positive mixture components) and normalizes each feature's column into responsibilities. When a feature's coefficient variance is tiny — for example when the reference group contains only two samples whose centered log abundances for that feature nearly agree — the Nelder-Mead optimization drives the component parameters (`kappa1`/`kappa2`) toward zero, all three densities underflow to exactly 0, and the normalization evaluates 0/0, producing NaN responsibilities. Those NaNs propagate into the mixture weights (`pi`) and onward into the quantile probabilities used by `_estimate_bias_var`, where NumPy raises.

Required behavior, matching the reference R ANCOMBC implementation:

1. Responsibilities that are undefined due to underflow (0/0) must be treated as zero. R's `.bias_em` explicitly replaces NA responsibilities with 0 for all three components. Equivalently: when a feature's responsibility normalizer (the column sum) is zero, all three numerators are already zero, and that feature's responsibility column must remain zero.
2. The related M-step degeneracy must be handled the same way: if the negative or positive mixture component receives zero total responsibility, its `l1`/`l2` update must be set to zero rather than evaluated as 0/0 (which would yield NaN).
3. The responsibility normalization must not produce NaNs or surface `RuntimeWarning: invalid value encountered in divide` for this input.

For the reproducer above, the call must complete without error, and the coefficients for covariate `g[T.b]` — the `Log(FC)` and `pvalue` values reported per feature in the returned result — must match the R ANCOMBC 2.12 reference values within 1e-6:

- Log fold change for f0, f1, f2: `[-1.08292235, 0.16646377, -0.13155807]`
- p-values for f0, f1, f2: `[0.25770796, 0.85244671, 0.87755871]`

The fix must be scoped to the degenerate regime: `_estimate_bias_em`'s behavior and results for ordinary, non-underflow inputs must remain unchanged. Making the computation underflow-proof in a more general way (for example by evaluating the Gaussian densities in log space so the responsibilities stay well-defined) is not the required behavior — in the degenerate regime the responsibilities must be exactly zero, as in R, and any approach that recovers nonzero responsibilities there will not reproduce the reference values above.

Work in `/workspace`. Submit your fix in the existing Python source files under `skbio/stats/composition/_ancombc.py`. Preserve the other public behavior. The environment is offline; dependencies are preinstalled. Grading runs the relevant repository tests in a fresh environment, using your submitted source files.
