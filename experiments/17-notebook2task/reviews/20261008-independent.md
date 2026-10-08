# Independent review and corrections

Reviewed commit: `8fe742a8b84c7022ca52a6f987c97007efe4c453`.
An independent agent reviewed explorer behavior, provenance, prompt claims, authoring and solver evidence, scientific claims and issue reporting. The reviewer did not edit files or launch evaluations. Review included bounded hash/conversion checks; it was not an exhaustive secret audit or scientific rerun.

| Finding | Correction |
|---|---|
| P1: SETA original trace was only in temporary storage | Preserve its original Pi stream as a 70,087-byte lossless gzip in Git, alongside selected native result fields. A retention manifest inventories both tasks' small public evidence, hashes and exclusions. Publication/download verification follows separately. |
| P2: BixBench Task displayed only the question | Display the full pinned Harbor instruction, including submission paths and XML tags; label adapter additions. |
| P2: BixBench executable verifier incorrectly called unavailable | Display the pinned Python judge and Bash launcher; keep the published reference record in its own card. No judge request occurred. |
| P2: SETA feature-selection defect understated | Annotation now records supervised selection before downstream CV and mismatch between k search and final feature-selection procedure. No bias magnitude is claimed and the held-out test is not invalidated by inference. |
| P2: All notebooks returned to Approaches | Back link explicitly sets view=notebooks and preserves filters. |

The reviewer independently regenerated both ATIF traces from native events and checked hashes/token totals and original prompt/task pins. A second read-only review found the substantive fixes appropriate and identified two stale labels, also corrected. Both browser checks passed after the fixes (SETA and BixBench separately), including BixBench instruction/judge/launcher/reference visibility, trace controls, mobile width and return navigation. Peak sampled browser RSS was below 428 MB. No solver, judge or scientific rerun was made; original reports and native rewards remain unchanged.

Open research questions: SETA source-version matching, magnitude of SETA CV optimism, BixBench reference-value discrepancy, verifier timeout cause, and transfer of the generated recipe. Private runtime configuration and model transport records are excluded from public retention; the public manifest does not claim a full mirror of the raw Iris archive.
