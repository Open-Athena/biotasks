## Proposed next design: PR mining plus a GLM performance filter

**Follow-up design only; not part of the resumed comparison.** Two distinct products are possible:

1. **Similarity corpus:** `pr_diff` → structural/reference checks → one blind GLM solve → retain selected reward bands and lineage. This is cheap and avoids per-task authoring, but rewards patch similarity. Low similarity can reflect a valid alternative implementation; it is not proof of difficulty or functional failure.
2. **Correctness corpus:** cheap PR discovery and source/test eligibility → `pr_runtime` before/after contrast → blind GLM solve → retain useful difficulty bands under executable test rewards. Where GLM is used earlier to prioritize candidates, its diff score is a screening signal only; functional verification remains necessary before admission.

The first screening metric should be both **yield of runnable tasks** and **GLM reward at fixed solver settings**, not simply “keep every task GLM fails.” Inspect execution failures separately, deduplicate historical fixes before splitting, and retain a small distribution of easy/medium/unsolved tasks if the goal is an RL curriculum. One attempt gives noisy, model-specific evidence: our 2,048-output-token/12-turn/15-minute solver measures this constrained GLM setup, not intrinsic task difficulty. More attempts or a larger solver allowance would be a new decision, not an automatic continuation.

The scalable part should be fixed code and deterministic filters, with the free endpoint supplying only the model stages. A GLM review stage could propose specification/coverage concerns, but it should not directly supply reward or substitute for executable controls. Count task-specific Codex repairs separately from allowed final assessment; a proposed filter does not retrospectively make the current 30 tasks autonomous outputs.

