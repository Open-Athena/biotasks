# Issue

**Title:** Float index arrays are silently truncated unless every value is a non-integer

## Description

### Please make sure these conditions are met

- [x] I have checked that this issue has not already been reported.
- [x] I have confirmed this bug exists on the latest version of anndata.
- [x] (optional) I have confirmed this bug exists on the main branch of anndata.

### Report

 / #1746. A float index array only raises when every value is a non-integer. If at least one value is a whole number, the rest get truncated silently, e.g. `adata[np.array([0.5, 2.0])]` returns observations 0 and 2.

The check in `_from_array` (`src/anndata/_core/index.py`) is

```python
if xp.all((indexer - indexer_int) != 0):
    raise IndexError(...)
```

I think that should be `xp.any`. The 0.11.2 release note says "Error out on floating point indices that are not actually integers", and numpy raises for any float index. `test_index_float_sequence_raises_error` only uses arrays where all values are non-integers, so it doesn't catch this.

Whole-number floats like `[0.0, 2.0]` still work with `any`, so that part wouldn't change. Happy to open a PR.

Code:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "anndata@git+https://github.com/scverse/anndata.git",
# ]
# ///

import anndata as ad
import numpy as np

adata = ad.AnnData(np.arange(12, dtype="float32").reshape(4, 3))

for index in ([0.5, 1.5], [0.5, 2.0], [0.9, 1.0]):
    try:
        print(index, "->", list(adata[np.array(index)].obs_names))
    except IndexError as e:
        print(index, "-> IndexError:", e)
```

Output:

```
[0.5, 1.5] -> IndexError: Indexer array([0.5, 1.5]) has floating point values.
[0.5, 2.0] -> ['0', '2']
[0.9, 1.0] -> ['0', '1']
```

Same output on 0.13.3.post0 from PyPI.

### Versions

| Package | Version                 |
| ------- | ----------------------- |
| anndata | 0.14.0.dev56+g4ded337f9 |
| numpy   | 2.5.3                   |
| pandas  | 3.0.5                   |
| scipy   | 1.18.1                  |

| Component | Info                                                                        |
| --------- | --------------------------------------------------------------------------- |
| Python    | 3.13.13 (main, Apr  7 2026, 18:19:01) [Clang 21.0.0 (clang-2100.0.123.102)] |
| OS        | macOS-26.6.2-arm64-arm-64bit-Mach-O                                         |
| Updated   | 2026-09-17 08:47                                                            |

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `9d6a4e221235` and running the modified tests.