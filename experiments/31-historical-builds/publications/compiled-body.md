Can rebuilding after historical resets restore correct-revision compiled code without per-task repairs? Follow-up to #28, initially scoped to MACS.

**Findings:** Original evidence confirms extension removal in seven paired validations. Both native validation and exported verification omit rebuilding. A synthetic compiled fixture now passes 12 checks through the pinned shell builders: a deterministic rebuild restores nop-fail/oracle-pass behavior, preserving a stale fixed-ref binary produces a false-positive nop, and a failed rebuild stops before tests.

**Baseline limitation:** the saved MACS reconstruction Dockerfile contains three syntactically invalid RUN commands; its smoke/fresh checks were false. Saved rebuild commands also contain unquoted version constraints. Establishing a faithful executable baseline is separate from testing the rebuild lifecycle; no recipe has been manually repaired.

**Next:** integrate an opt-in general hook through native and exported paths, exercise failure guards and graded verification, then compare one frozen original MACS removal case if its baseline can be reconstructed under the declared scope. No biological PR recovery is claimed.

**Bounds:** no additional LLM repair loop or per-PR environment fixes. Work so far uses local syntax/compiled-fixture checks only: zero model calls and no remote jobs. Original evidence stays immutable; research remains separate from main.

[Findings and limitations](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/findings.md) · [Compiled fixture results](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/compiled-lifecycle-results.json) · [Original evidence](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/lifecycle-findings.json) · [Full scope](https://github.com/Open-Athena/biotasks/blob/397b7769c362c689a0714a5d1f014a6830b72cb9/experiments/31-historical-builds/issue-scope.md). Detailed updates remain in comments.
