Audit the supplied validation operations for false acceptance. Return one finding
for every exact operation ID in coercion_operations. Use the complete public
instruction and grader source in audit_documents; do not infer correctness from
prior passing controls or from a previous positive review.

For each conversion, trace whether it operates on submitted data, trusted
reference data, or internal bookkeeping. Decide whether it preserves all values
required by the public contract, or can erase a meaningful error before the
comparison. Consider fractional values truncated to integers, non-Boolean values
converted by truthiness, rounding, clipping, and missing-value replacement.
Do not reject legitimate alternative storage representations merely because
they use another numeric dtype. Distinguish numeric equality from coercing an
incorrect submitted value into a correct one.

Use safe only when the surrounding validation independently rejects relevant
wrong values or the conversion cannot hide a contract violation. For
false_acceptance, explain a concrete wrong-value construction and why every
other relevant assertion would still accept it. Propose your own repair that
preserves the biological methodology and valid alternatives. If evidence is
insufficient use unknown and explain the missing evidence. Do not edit files.

A later comparison of already-cast values does not validate original submitted
values or a promised Boolean representation. For truthiness casts, consider
non-binary nonzero numbers as well as strings: they can match the entire expected
Boolean pattern while the original values violate a Boolean-field contract.
Check the original values or dtype where the contract requires that; distinguish
an explicitly permitted 0/1 encoding from arbitrary truthy values. Do not infer
permission for a representation solely because the current grader accepts it.
