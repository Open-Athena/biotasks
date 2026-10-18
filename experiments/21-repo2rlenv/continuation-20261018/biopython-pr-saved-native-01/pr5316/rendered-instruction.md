# Issue

**Title:** Issue #5193 - Add __hash__ to CompoundLocation

## Description

Adds `CompoundLocation.__hash__`, following on from `SimpleLocation.__hash__` earlier on this branch, so `Location` objects can be used in a `set` or as `dict` keys.

`__hash__` is based on `operator` and `parts`, matching `__eq__`. Since it relies on each part's `SimpleLocation.__hash__`, the same `ref`/`ref_db` limitation applies here too. Tests cover hash/eq consistency (including fuzzy and unknown positions) and set membership.

- [x] I hereby agree to dual licence this and any previous contributions under both
the _Biopython License Agreement_ **AND** the _BSD 3-Clause License_.

- [x] I have read the ``CONTRIBUTING.rst`` file, have run ``pre-commit``
locally, and understand that continuous integration checks will be used to
confirm the Biopython unit tests and style checks pass with these changes.

- [x] I have added my name to the alphabetical contributors listings in the files
``NEWS.rst`` and ``CONTRIB.rst`` as part of this pull request, am listed
already, or do not wish to be listed. (*This acknowledgement is optional.*)

Closes # 5193

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `bbc55712db23` and running the modified tests.