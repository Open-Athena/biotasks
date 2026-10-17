# Issue

**Title:** `ancombc2`: "Quantiles must be in the range [0, 1]" when the bias E-M responsibilities underflow to 0/0 (R sets them to 0)

## Description

**Versions:** scikit-bio 0.7.4 (also unfixed on `main` at 71286a24bd; `_estimate_bias_em` last changed in 9494b7de6f), NumPy 2.5.3, SciPy 1.18.1, pandas 3.0.6, Python 3.13.2.

**Repro**
```python
import pandas as pd
from skbio.stats.composition import ancombc2
X = pd.DataFrame([[154, 188, 68], [143, 63, 177], [30, 154, 96], [131, 167, 150]],
                 index=list("abcd"), columns=["f0", "f1", "f2"])
md = pd.DataFrame({"g": pd.Categorical(["a", "a", "b", "b"])}, index=list("abcd"))
ancombc2(X, md, "g", p_adjust=None)
# RuntimeWarning: invalid value encountered in divide (_ancombc.py, `resp /= np.sum(resp, axis=0, keepdims=True)`)
# ValueError: Quantiles must be in the range [0, 1]
```

**Cause.** With two samples in the reference level whose centred log abundances of a feature nearly agree, that
feature's `var_hat` is tiny. Nelder-Mead drives `kappa1`/`kappa2` to 0, all three Gaussian densities underflow, and
`resp /= resp.sum(0)` gives 0/0 = NaN. NaN reaches `pi`, the loss comparison stops the loop, and `np.quantile` raises.

**Expected (R, ANCOMBC 2.12, same arguments):** R's `.bias_em` sets the NaN responsibilities to 0
(`r0i[is.na(r0i)] = 0`, likewise `r1i`, `r2i`) and returns lfc -1.08292235 / 0.16646377 / -0.13155807,
p 0.25770796 / 0.85244671 / 0.87755871.

**Proposed fix:** after the division, under `np.errstate(invalid="ignore")`, `np.nan_to_num(resp, copy=False, nan=0.0)`.
With it, scikit-bio matched R to 6 decimals on this table and on 15 of 16 failing random tables (the 16th differs by
0.011; both runs reach the 100-iteration E-M cap). Found via biotapy's property tests (about 0.16% of random 6 x 7
tables with a two-sample reference level).

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `71286a24bddf` and running the modified tests.