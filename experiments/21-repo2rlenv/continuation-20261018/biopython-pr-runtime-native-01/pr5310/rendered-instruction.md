# Issue

**Title:** `SeqUtils.molecular_weight("")` returns +18.0153 instead of 0 or an error

## Description

The molecular weight of an empty sequence is not physically defined. But actual behavior is:

```python
>>> from Bio.SeqUtils import molecular_weight
>>> molecular_weight("", "DNA")
18.0153
>>> molecular_weight("", "RNA")
18.0153
>>> molecular_weight("", "protein")
18.0153
```

Suggested fix:

```python
if not seq:
    return 0.0
```

or raise `ValueError("sequence is empty")` if a zero-length input should be treated as invalid.

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `dc262b5c437e` and running the modified tests.