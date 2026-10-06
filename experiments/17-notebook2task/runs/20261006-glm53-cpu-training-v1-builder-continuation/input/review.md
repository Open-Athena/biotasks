# Parent review before builder

Preserve raw GLM draft unchanged. Clarify scientifically consequential defects:
mean fold AUC is not pooled OOF AUC; a fixed HistGradientBoosting reference does
not permit alternative implementations; no tolerance was measured by the model.
Make row/feature order, IDs, JSON nesting, EDA definitions and report requirements
explicit. Correct prediction row counts and membership wording. Keep mutation
controls outside graded tests so empty submissions cannot earn vacuous credit.
Require a runnable pipeline for a separate parent reproducibility check, without
executing solver code in a privileged hidden-data verifier.

These are parent-authored repairs to the idea output, not unassisted GLM changes.
See the complete diff. Threshold and runtime validity remain to be measured.
