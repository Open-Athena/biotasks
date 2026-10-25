# Unattended PR workflow: bounded delivery

The supported candidate now completes the official PR-to-task workflow without Codex in its execution loop: frozen PR discovery, upstream bootstrap/generation, local export, independent deterministic controls, cumulative accounting, append-only eligible HF archival and ownership-scoped cleanup. Draft [PR #63](https://github.com/Open-Athena/biotasks/pull/63) contains the fresh-main-based implementation. Main remains unchanged; this is a reviewable delivery, not a merged tool or dataset release.

The decisive fresh case is [NiBabel #66](https://github.com/Open-Athena/biotasks/issues/66), whose [complete evidence](https://github.com/Open-Athena/biotasks/blob/0d7344963b050bf3743de14d4d6858039c2c6201/experiments/66-fresh-nibabel/results.md) records one original generation, one control workflow/two sides, all four HF readbacks, empty owned resources and byte-inert installed completed replay. Nop reward 0 fails 9/9 target regressions; oracle reward 1 passes 9/9, with 37/37 P2P passing on both sides and oracle exit 0. The selected test-file command is clean, not every NiBabel test. No source/test/dependency/parser/reward/timeout repair or added model stage occurred between generation and controls.

The existing DendroPy export has a separate tracked positive pair, but four untracked failures on both sides keep it ineligible for the strict clean-command profile. AnnData, Biopython and Cobrapy negative outcomes remain unchanged and useful: installation/import binding, removal of compiled extensions, saved APT state and verifier deadlines can invalidate generation or reconstruction. These are pipeline/environment boundaries, not evidence that every historical PR was tried or that a model alone caused every failure. The original cohort remains 83 exports, 82 ever-positive and 67 ever-clean, with 93 pair slots; slots are not unique tasks. All 83 recorded base/head and ten-file identities are reconciled; six original builds remain absent.

## Changes and why they exist

Official source stays pinned to Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. The original built-in model calls, native parser, reward and deadlines remain. The candidate's differences are explicit rather than a claim of unmodified upstream execution:

| Change | Purpose and limit |
| --- | --- |
| Manifest/SDK/source identities, serial ledger and original-call cost observation | Execute/recover finite cases without a research-specific launcher or hidden extra model stage; unknown effects/costs hold instead of substituting a new job. |
| Approved Docker resource/network/ownership wrapper | Fit upstream's environments and fresh-image check to existing reserved TRC CPUs and clean only owned resources. |
| Explicit official boolean option and optional generic pytest argument rooting | Admit assertions added inside an existing test and anchor appended paths under the workspace. No source/test/import/dependency repair; omitted options retain the baseline. |
| Local-ready transition scheduling | Avoid an unnecessary five-minute wait after evidence is already present; native execution deadlines are unchanged. |
| Unambiguous cache matching and disposable staging normalization | Handle mixed-case repository paths versus lowercase Docker tags while preserving original raw/cache/grading bytes. |
| Strict read-only import of known sealed generations | Reuse fully billed/archived/cleaned evidence across a qualified local connector change; active, unknown, partial or held generations remain rejected. |

The generic APT experiment, source-provenance instrumentation, compiled rebuilding and subtest-parser proposals were not silently included in the supported candidate. Their evidence and limitations stay separately reviewable.

## Verification and spending

PR #63 at `c19e73697fd5a56cee4670418fb9785d0b033b3f` passes 186 local tests, including actual distribution/install and CLI invocation outside the checkout, plus lint, formatting, types and hooks. Both GitHub CI checks pass. Tests cover multiple/zero candidates, zero exports, source/input drift, interruption/uncertain effects, unknown or overrun accounting, archive/cleanup retention and inert recovery. Fixtures are distinguished from the fresh native evidence above and the earlier unchanged existing-export controls.

| Repository | Original model calls | Actual OpenRouter cost |
| --- | ---: | ---: |
| Cobrapy | 11 | $0.287646 |
| AnnData | 9 | $0.313983 |
| Biopython, two declared comparisons | 23 | $1.033545 |
| DendroPy | 5 | $0.087849 |
| NiBabel | 13 | $0.473580 |
| Total incremental epic usage | 61 | **$2.196603** |

A separately recorded zero-attempt Cobrapy submission incurred no model charge. Total allocated reserved CPU use is **14.892111111/32 CPUh**; no new capacity or accelerators were purchased. CPU/model reservations are zero and paid model execution is disabled. The conservative **$10 storage reserve remains unreconciled**, so it is not presented as zero storage cost. Actual plus that reserve remains below the $90 operating ceiling and strictly below the user's $100 extra allowance. `budget.json` and `model-cost-by-run.json` preserve exact accounting.

## Review boundary

This is one supported execution profile and a small selected integration set, not a population-yield estimate, universal language/backend support, learned-solver score or production/training/dataset release. Source/import provenance, compiled rebuilding, subtest identities and argument/parser edge cases remain documented limitations. Future adoption or experiments require their own review and unchanged budget/authorization boundaries. Do not keep launching cases just to obtain another success.

All admitted workflows are terminal, eligible evidence has verified HF readback and owned cleanup, and the final installed replay is inert. Keep the epic, children and all five pipeline PRs open for human review; #28 remains closed. No automatic merge, release or further run is part of this delivery.
