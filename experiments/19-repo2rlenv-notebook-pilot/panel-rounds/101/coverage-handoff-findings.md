# Coverage handoff finding from the frozen common-version round

The original COBRApy 196 task was rejected; it remains unchanged. Its preparation inventory conflated two different claims: a result cannot be saved by the append-only preparation step, and a result is not required scientifically. The specification stage had the complete original source and an explicit instruction to reconsider missing exports, but retained the mistaken exclusion. Final source review caught the missing branch after construction and grading.

The proposal deliberately separates these stages: preparation saves existing named results without editing the source, while construction may faithfully recompute an eligible missing result. The append-only restriction is therefore intentional. The defect is an ambiguous exclusion handoff and an unsupported subsumption claim, rather than a need to let preparation rewrite the analysis.

## General next-version change under consideration

Clarify preparation's existing `excluded_outputs` field without adding another inventory or changing its append-only code contract. For each meaningful outcome not exported, distinguish a scientific non-target from an eligible result that is merely unavailable at script completion. The latter needs its original source location and why direct serialization is unavailable; it remains required for the later source-coverage audit. Preparation must not perform the recovery itself or claim that it has been executed.

Strengthen the specification and its independent review at the same boundary. A required result is represented by an actual output, an explicitly supplied upstream intermediate with substantial downstream science, or a blocked task. A different analysis does not subsume it merely because both use the same input or one covers a larger population. A subsumption claim needs the same scientific operation, entities, input state and meaningful result fields, with an explicit counterpart. Non-persistence, inconvenient storage and absent preparation exports are not scientific exclusion reasons. Preserve justified diagnostics and mechanics-only exclusions; do not turn every source call into another target.

This remains a candidate for the next scientific version, not a change to the frozen 232-file round or a manual fix to its generated tasks. Do not add notebook names, package functions, gene lists or expected values to shared prompts. Do not add scientific regex heuristics to the structural operation-accounting validator. Its complete call-site accounting cannot prove scientific equivalence.

## Checks needed before adoption

- Confirm that this is a shared handoff problem across the complete round, rather than infer general reliability from one rejection.
- Review the wording against independent outcomes, true subset views of the same result, overwritten results, plot-only computations and supporting diagnostics.
- Keep original-source execution and append-only export identities unchanged; do not move recovery into the preparation stage.
- Exercise a fresh source-only campaign on the new version and require independent source coverage, meaningful controls, native validation and original evidence readback. A prompt edit or a passing schema test alone is not scientific validation.

The original [result](result-196.json) and [performance record](performance-196-detail.json) remain the evidence. The failed key-order probe was rejected overall by a content check, so it is a separate attribution defect; it is not evidence that the grader accepted a wrong answer.
