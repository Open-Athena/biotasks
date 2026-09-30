# Authoring migration logbook

## 2026-09-30 — frozen source and scope

The local and GitHub heads of `codex/bio-tasks-authoring` agreed at
`37973a95c71d5e1d38bb15c238f1d40369255359`. The source checkout was clean,
including untracked files outside ignored directories. The migration issue's
drafting-time comparison-manifest and round-two/round-three additions were
committed by `c97c2469120f91931fdec648714a755d20604b47`. No owner checkout is
modified or resumed by this migration. Recheck the source before final handoff;
record later additions separately if it moves.

The integration-to-head delta has 482 paths, all within
`docs/experiments/bio-task-generation/`, with no source-ranking `01-discovery/`
material. Preserve the complete 487-file subtree to retain five unchanged
context pages, plus the initial discovery template from the integration commit.
Every changed path has a byte-identical migrated disposition in
[migration.json](migration.json). No scientific output or historical hash is
rewritten. Four local Python helpers are preserved as non-executable `.py.txt`
snapshots; the remaining ignored artifacts have an explicit inventory and
retention requirement.

The first lightweight source handoff counted 71 ignored files. This capture
has 73 files totaling 8,912,921 bytes; the two later handoff records explain the
increase. This inventory is not automatically an upload allowlist. Public
archival requires file-level review, an exact manifest and verified retrieval.

## Candidate decisions

The default decision is to continue research on this branch, without a promotion
PR. A source-side design choice is not itself evidence that a supported
pipeline change succeeds. The candidate files at `src/biotasks/prompts/` retain
the source head for future comparisons. Promotion from current `main` remains
separate and requires the stated missing evidence below.

| Candidate | Decision | Evidence and missing validation |
| --- | --- | --- |
| General source-access fallbacks and an entry-level inspection queue | Defer promotion; retain candidate | [Bedtools 05](baseline/prompt-experiments/2026-09-29-bedtools-luna-05/index.md) recovers pinned evidence; [06](baseline/prompt-experiments/2026-09-29-bedtools-luna-06/index.md) broadens coverage but regresses data identity and roles. Need repeated source-fidelity and downstream authoring comparisons. |
| Single explorer with record-specific self-checks | Retain research design; defer reliability claim | [Round one and subsequent repeats](baseline/prompt-experiments/index.md#round-1-results) still contain semantic failures despite passing structural checks. Need independently audited handoffs used by an author. |
| Separate reconciliation worker | Reject as an active pipeline stage | [Four historical trials](baseline/prompt-experiments/index.md#earlier-trials) repair identities but leave copied dependencies, broad boundaries and stale source maps. The source decision retains one worker; no equal-total-cost advantage or authored-task success was demonstrated. Preserve every trial. |
| Exact identifiers, asset identity, processing state and final-map consistency clauses | Defer promotion | [Round two](baseline/prompt-experiments/index.md#round-2-results) has gains and regressions; identical-prompt round-three repeats show instability. Bundled changes do not isolate individual clauses. Require multiple independent cases and repeated review. |
| Operation-level units, including conversion/extraction; catalog accounting | Retain candidate; defer supported default | [UCSC catalog trial](baseline/prompt-experiments/2026-09-30-catalog-ucsc-luna-high/index.md) finds withheld examples and accounts for 328 entries, but 283 remain pending, help versions conflict, and effort/runtime differ from earlier trials. Need cross-repository replication and source-backed field review. |
| Remove artificial per-repository time/unit caps | Retain source research preference; defer completion claim | [Uncapped comparison](baseline/prompt-experiments/2026-09-30-uncapped-model-effort-comparison.json) still has premature stopping. Real resource/service limits remain binding. Need a scoped experiment showing reliable completion; no unbounded execution is authorized here. |
| Default model or reasoning effort | Defer | One DESeq2 matrix, one run per cell, three completed and one service-blocked. Requested settings, token counters and wall time are observations; served settings and billed cost are unknown. No complete within-Sol effort comparison or general ranking follows. |
| Separate source tool-role from solver work; broader author-task input types | Defer promotion | [Authoring prompt](baseline/prompts/author-task.md) clarifies the contract but has no authoring trial. Need native reference execution, meaningful wrong-submission checks and independent solving for proposed focused/integrated cases. |
| Proposal/construction/repair workflow, solve and reflection roles | Defer implementation | [Guidance](baseline/task-authoring.md#prompt-and-run-versioning) is a design; no reflection template, maintained orchestration or validated new Harbor tasks exists. The earlier proposal-only template remains historical. |
| CLI wrapper and temporary preparation/checking helpers | Reject wholesale runtime promotion | Captured after the batch; per-run wrapper hashes were not recorded. Absolute paths, output-writing behavior and service assumptions prevent treating it as a portable maintained runner. Recover as audit evidence only. |
| Testbed and authoring/discovery guidance changes | Defer standalone promotion | Preserve distinctions between operations and tasks, source and solver roles, source-use terms and data eligibility. Validate affected prompt behavior before consolidating a supported specification; avoid importing experiment status into `main`. |

## Interpretation limits

The earlier reconciliation worker's readiness recommendation was contradicted
by its own saved artifacts and the parent review. Preserve both statements.
Structural success never overrides the source/scientific defects. The source
reviews are independently authored relative to the workers, but this migration
does not claim a fresh exhaustive audit of every unit.

Earlier collaboration workers lack full event traces and usage. The CLI matrix
retains compressed execution events, metrics, completed responses, and the
Sol/high failure/partial output. Its preflight failures and service failure are
distinct from completed results. Prepared-but-withdrawn comparison cells remain
in their configuration records and must not be counted as executions.

The DESeq2 two-versus-six sample question depends on the tximportData version;
preserve the source's later correction rather than silently rewriting the
earlier review. Source-provided artificial condition labels, raw/transformed
state and reference-versus-observation identities remain scientific review
criteria. No rerun of a model or scientific package occurs during migration.

## Publication and archival

Research publication, durable cache archival and any continuing issue are
separate steps. No promotion PR is currently warranted. Record the final
committed/pushed/PR/merged state and source-head recheck with the handoff.
Retain the Marin source branch and all original local evidence until archival
verification and explicit disposition are complete.
