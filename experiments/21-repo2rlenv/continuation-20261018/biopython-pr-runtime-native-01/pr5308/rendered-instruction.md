# Issue

**Title:** Issue #5193 - Add __hash__ to SimpleLocation

## Description

Implemented ` __hash__` based on `start`, `end`, `strand`, `ref`, `ref_db` matching the attributes used by `__eq__` in `SeqFeature.py`. Add tests covering hash/eq consistency and set membership in `test_SeqFeature.py`.

- [x] I hereby agree to dual licence this and any previous contributions under both
the _Biopython License Agreement_ **AND** the _BSD 3-Clause License_.

- [x] I have read the ``CONTRIBUTING.rst`` file, have run ``pre-commit``
locally, and understand that continuous integration checks will be used to
confirm the Biopython unit tests and style checks pass with these changes.

- [x] I have added my name to the alphabetical contributors listings in the files
``NEWS.rst`` and ``CONTRIB.rst`` as part of this pull request, am listed
already, or do not wish to be listed. (*This acknowledgement is optional.*)

Addressed part of #5193

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `dc262b5c437e` and running the modified tests.