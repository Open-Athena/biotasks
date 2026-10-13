# Design review 005

One design-only GLM-5.3 call on the unchanged seed and prompt from 004, changing only reasoning effort from low to high. JSON schema passes. The response used 3,787 reasoning tokens versus 174 in 004; this is a single uncontrolled sample per setting, not a causal reliability estimate.

Design review still fails: the proposed PCA test needs loading vectors absent from the output contract; numerical and overlap tolerances remain invented; upstream normalization checks are sampled without adequate coverage justification; added marker-set averaging changes the roles of source annotations without acknowledging that change. Some source/adaptation claims and runtime guarantees are unsupported. Stage-specific QC and raw-count verification improved.

Preserve the response unchanged. The next revision simplifies the prompt around a single public contract plus a requirement-to-verification matrix. No seed-specific methods or expected answers are added. No construction, native validation, solver or viewer update occurred.
