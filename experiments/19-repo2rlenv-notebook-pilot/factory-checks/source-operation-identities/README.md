# Distinct identifiers for every source call

Python chained calls can share their starting source coordinates. The previous start-only IDs collided, so converting the inventory to a dictionary silently replaced one call with another. The updated inventory disambiguates only shared starts with each call's end coordinates, preserving previously unique IDs. Admission rejects duplicate IDs rather than silently losing an operation.

Single-line and multiline synthetic chains, stable unambiguous IDs and rejection of ambiguous inventories have regression coverage.38 focused source/materialization/review tests pass. Hash-bound static inspection of all ten original panel sources found legacy collisions in six and retains every literal call with a unique ID after correction. No source program or generated task was edited or executed by this check.

This is syntactic provenance, not a runtime DAG, scientific eligibility decision or proof that ID collisions caused any particular omission.167 used its earlier frozen runtime; its independent scientific review correctly rejected a missing nonredundant endpoint despite the old IDs. Original run evidence remains unchanged. [Validation](validation.json), [ten-source identities](ten-source-static-check.json).
