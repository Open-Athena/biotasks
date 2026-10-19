# Automatic pipeline evaluation protocol

## Automatic-pipeline comparison: generation versus final assessment

**The goal is to assess the automatic pipeline. Manual assessment of its final outputs is allowed; manual fixing is not.** A successful result is an unchanged output of a frozen declared pipeline configuration that passes the post-run assessment. Codex reading the result, judging quality, or writing separate diagnostic controls afterward does not by itself disqualify it. My earlier claim that manual assessment prevented an automatic-pipeline success was too strict and is superseded by this rule.

The pipeline may use its own bounded automatic repair loops. Codex must not edit a candidate’s instruction, learner source, reference solution, tests, verifier, fixtures, dependencies or runtime assets after a failure, nor supply task-specific author feedback. A task that needs such intervention is an automatic-pipeline failure; any historical assisted recovery remains separate evidence. Generic endpoint authentication, fixed resource limits, capture and cleanup are execution plumbing, recorded before a run. They must not alter the task’s intended content or behavior. Freeze repository profiles and input selection before the batch; a task-specific workaround discovered during the batch is not silently added to its successful outputs.

### How to read the existing 30-task ledger

The 30 previously accepted/scored tasks combine automatic outputs with assisted runtime recoveries and one known task-specific author-feedback revision. **They are not a total of 30 proven automatic-pipeline successes.** They remain preserved for provenance and solver evidence. We must assess unchanged original outputs separately; unknown provenance stays unresolved rather than being treated as either success or failure. Original target/candidate allowances are retained, including failed and uncertain requests.

| Existing evidence | Implication for the automatic comparison |
| --- | --- |
| Esty and observed-features acceptance receipts explicitly retain the emitted instruction/source/reference/grader bundle unchanged | These are evidence of unchanged pipeline outputs with final manual assessment. Review alone is allowed. Full run configuration/feedback lineage still needs to accompany the primary accounting. |
| Tsallis, Pielou and Enspie retained original GLM instructions without task-specific author feedback | Positive authorship evidence. Check the complete exported/runtime bundle before claiming unchanged end-to-end output; unchanged prose alone does not establish that. |
| New LCC instruction was revised by GLM using task-specific feedback written by Codex | Excluded from primary automatic-output success; retain the original failure and label the revised task assisted. |
| First LCC, R2E-Gym and portable historical profiles required explicit build/fixture/runtime work | Report the original pipeline outcome and adapted-profile evidence separately. Do not use a rescued runtime as proof that the original configuration worked. |
| PR-diff: all 108 original assets across the 12 selected tasks match their export hashes after removing only two identical tmux/offline suffixes; Scaler used a hand-prepared family | PR-diff content is automatic and unchanged. Its runtime result uses that shared adapted profile. For Scaler, distinguish automatic instances from family preparation. Do not infer unchanged stock-runtime success or automatic scientific-family creation. |

The task-table provenance letters remain descriptive: **D** native similarity export; **H** historical task with portable/runtime adaptation; **U** explicitly unchanged emitted bundle; **G** unchanged GLM instruction; **F** task-specific author-feedback revision; **A** explicit runtime/build/fixture adaptation; **S** instances from a hand-prepared Scaler family. Review/control preparation is recorded independently of these task changes.

### What “validated” means here

| Stage | Who/what performs it | Meaning for this comparison |
| --- | --- | --- |
| Native generation checks | The pinned pipeline builds/runs its own tests or before/after contrasts | Automatic pipeline evidence; successful export alone does not guarantee task quality |
| Final instruction/source assessment | Codex reads the completed unchanged output and its pinned source/tests | Allowed final assessment; may accept or reject, without fixing or giving feedback to generation |
| Additional diagnostic controls | Codex may prepare separate correct/incorrect/partial submissions and run the unchanged grader | Assessment evidence, not a task repair; record which checks were performed and their finite coverage |
| Blind GLM solve | Existing free GLM, fixed solver limits, deterministic original reward | Model performance on that exact task; no repair of the task or solver attempt |
| Marin checks | Recorded schema checks or explicit native/Marin runtime pairs | Integration evidence kept separate from original automatic task-generation yield |
| Hash/readback/cleanup checks | Programmatic accounting | Preservation and lifecycle evidence, separate from scientific quality |

“Independently accepted” in earlier records means evaluated separately from generation with Codex involvement; it does not mean an external human audit or exhaustive scientific correctness. The numerical reward is computed by code. Final manual assessment is permitted under the current experiment rule. The deferred end-to-end grader-integrity diagnostic remains unexecuted.
