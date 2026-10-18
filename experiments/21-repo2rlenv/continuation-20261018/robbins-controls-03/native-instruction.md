## `skbio.diversity.alpha.robbins` returns an integer instead of the Robbins estimator

### Observed behavior

`robbins(np.array([1, 2, 3, 0, 1]))` returns `np.int64(14)`.

### Expected behavior

`robbins` should compute Robbins' estimator of the probability that the next observation belongs to a feature not yet seen, defined as `F1 / N`, where:

- `F1` is the number of singletons (features whose count is exactly 1), and
- `N` is the total number of observations (the sum of all counts).

For the count vector `[1, 2, 3, 0, 1]` there are 2 singletons and 7 total observations, so the correct result is `2/7` (`0.2857142857142857`), returned as a floating-point value exactly equal to `2/7`.

Since `F1 <= N` for any nonnegative count vector, the result must always lie in the closed interval `[0, 1]`. A return value of `14` is outside that range, and the integer return type (`np.int64` rather than a float) indicates the estimator is not being produced as a ratio.

### Reproducer

```python
import numpy as np
from skbio.diversity.alpha import robbins

counts = np.array([1, 2, 3, 0, 1])
result = robbins(counts)
print(repr(result))     # observed: np.int64(14)
print(result == 2 / 7)  # expected: True, since 2/7 = 0.2857142857142857
```

### Boundary case

For a count vector containing no observations at all (e.g., `[0, 0]`), both `F1` and `N` are 0 and the estimator is undefined; `robbins` is expected to return `NaN` for such input. A correct fix must return `NaN` for a zero-total count vector.

Work in `/workspace`. Submit your fix in the existing Python source files under `skbio/diversity/alpha/_base.py`. Preserve the other public behavior. The environment is offline; dependencies are preinstalled. Grading runs the relevant repository tests in a fresh environment, using your submitted source files.
