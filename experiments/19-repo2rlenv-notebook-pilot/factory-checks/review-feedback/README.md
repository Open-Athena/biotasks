# Actionable review-validation feedback

The canonical next version now reports missing, unexpected and duplicate hint IDs in the existing validation failure. It preserves the coverage condition and refusal to accept exposed or unresolved hints. Code does not invent an ID, assessment, rationale or scientific verdict. The review prompt requests actual nested JSON values and verbatim opaque IDs, and forbids changing a scientific conclusion merely to satisfy the response schema.

The original 197 failure remains unchanged: 18 executed controls passed, but final review timed out after repeated malformed nested JSON and one missing/unexpected identity among 55 assessments. Passing those controls never qualified the task.

`candidate.py` reproduces the exact original two-file patch against pinned baseline 23fd6d27 without modifying canonical files. Its tests now compare that original validator with the actual canonical validator across 1,080 coverage/scientific-verdict scenarios. They also test 55-item typo diagnostics, duplicate IDs, refusal to clear exposures, unchanged files during patch generation, and exact correspondence between canonical code/prompt and the reviewed patch. The original five-test record remains in `offline-checks.json`; [next-version checks](adoption-checks.json) include 149 affected tests and six current diagnostic regressions.

This is a canonical next-version adoption, not a fresh model result or retroactive acceptance of 197. The currently running 103 campaigns use their frozen original sources and prompts. Fresh source-only execution, retained failures, unchanged bounded repairs, independent scientific controls, native trials and release checks remain required. No actual grader feedback is revealed to a blind probe author by this change.
