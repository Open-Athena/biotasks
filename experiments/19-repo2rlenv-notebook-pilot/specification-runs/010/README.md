# Specification 010: delivered, but not accepted as a complete contract

The source-inspection session completed and returned `draft_ready`. Operator review does not accept that disposition. The worker corrected the previous feature-selection and relabeling errors, but the combined specification/grading proposal still makes unsupported claims. No generated text has been manually repaired.

- [Generated review](review.md)
- [Generated public brief](task-brief.md)
- [Generated validation plan](validation-plan.md)
- [Inspection sequence](inspection-summary.json)
- [Original-file identities](artifact-manifest.json)

Factory checkpoint: `7c01068e7ea5e6ba6702d31b60740928642762b4`. The canonical prompt is unchanged from `c11b4f76e665c5a39457d2492b15746c26214db3`; the input/tool contract remains specification-inputs/007. Verified the actual initial API request against both. GLM-5.3 medium used 122 calls: 65 file reads, 56 searches and one artifact submission, with no invalid-tool response or repair submission. Worker time was 2787.83 seconds (46 minutes 28 seconds). The remote task and local clients are terminal.

## Improvements

The public feature-selection procedure now follows the top-N mode without incorrectly imposing the ignored mean/dispersion cutoffs. The relabeling example keeps named per-cell lineage annotations unchanged instead of reapplying a fixed numeric lookup after renaming communities. The response is substantive, readable and schema-valid. These improvements do not establish the rest of the scientific contract.

## Remaining findings

1. **Exact partition portability is asserted without evidence.** The public brief says seeded execution is deterministic and requires exact cluster membership after label alignment across conforming software stacks. A fixed seed alone does not establish identical random-number streams, approximate-neighbor choices or numerical behavior across implementations. The earlier successful reference execution is not independent portability evidence. The contract must distinguish an exact reference target from an empirically supported equivalence for other conforming implementations; the prompt explicitly requires evidence for the latter.
2. **The independent alternative does not cover the complete task.** Validation C.5 recomputes differential-expression statistics using submitted cluster assignments. That can check the DE branch, but does not independently produce the graph, partitions, embedding or lineage assignments from public inputs. The proposed cross-platform runs of the same stack also do not satisfy the requested independently computed alternative for those branches. Thus the full-task software-portability claim remains unsupported even as a validation proposal.
3. **The verifier-runtime conclusion is invalid.** C.5 infers that normalization plus DE recomputation exceeds 120 seconds because the full reference pipeline took about 148 seconds. A whole-pipeline measurement is not a lower bound for one subset of its operations. Runtime of the proposed verifier remains unmeasured. Sampling also must preserve the full multiple-testing correction family rather than silently change the statistical procedure.
4. **Harness execution is not proof that the scientific procedure ran.** C.6 says the harness enforces pipeline execution when discussing copied answers. A command-execution harness does not establish which scientific computations produced an artifact. Grading can check outputs and enforce isolation of reference assets; it cannot infer execution provenance from a correct file alone.

These are sufficient to withhold acceptance, not an exhaustive verification of every implementation detail. Static inspection also does not establish scientific correctness of the notebook's manual labels or numerical portability. No construction, scientific rerun, solver or viewer update occurred.

## Workflow assessment and pending decision

This run demonstrates that read-only inspection and artifact delivery work, but the combined assignment is expensive and still overclaims. The user asked whether the approach is fundamentally stuck. The proposed simplification is to draft analysis instructions and output schemas first, using reference methods as anchors, and establish tolerances and acceptable implementation variations through a separate executable validation step. Software choice would remain open. That change is a proposal awaiting the user's answer, not an adopted pipeline change. No replacement session is launched while this scope decision is pending.

## Evidence retention

All eight copied original files match the remote export manifest. The complete 122-call event trace was recovered and hash-verified. The bounded diagnostic transfer recovered 49 raw responses; response-summary.json explicitly describes that subset and is not a total-token report. All original model/tool records and verified package distributions remain in the remote archive. Inspection-summary.json is a derived navigation view; original generated files remain unchanged.
