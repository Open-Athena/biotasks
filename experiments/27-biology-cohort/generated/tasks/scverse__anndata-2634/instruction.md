# Issue

**Title:** chore: use memory store in tests

## Description

I try to resolve the problem "what if our zarr tests didn't take so long and we also didn't write SO much data during testing" by moving to memory stores where possible - there is still a test explicitly for local storage in `tests/test_readwrite.py::test_readwrite_equivalent_h5ad_zarr` (or where appropriate to not change) but otherwise, this should provide a big speedup!

- [ ] Closes #
- [ ] Tests added

- [x] Release note not necessary because: testing change

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `d75540e9136f` and running the modified tests.