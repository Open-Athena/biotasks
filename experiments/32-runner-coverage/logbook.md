# Issue 32: runner-coverage

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — parser fixtures and deterministic reject sample

Checkpoint `3ce0df02` parser comparison passes12expected-status fixtures plus two exact-source targeting checks in0.04seconds/20,244KiB. ANSI SGR stripping recovers synthetic colored statuses, but partial logs remain parseable and need an independent completion gate. No original task regrading. Sample frozen before acquisition: PR263,1605,371,250,1735,204. All six current public diffs acquired under2MiB cap; all still score zero with the pinned function recognizer. Four add net Perl test invocations. Original diff bytes were not retained, so current-source hashes and descriptor path agreement are reported rather than exact historical equality. Raw fixture-bearing diffs stay local; public findings contain paths/hashes/metadata only.

## 2026-10-23 — completion gate

Checkpoint `7e54cb90` runs seven synthetic sandbox-result cases through exact original/candidate native validation functions. The pinned validator accepts all seven; six contain nonzero execution or missing output markers. The candidate rejects those six and preserves the complete pair. Check completes in 0.04 seconds / 15,228 KiB. This confirms a control-flow mechanism, not an original task regrade; parser normalization must not be used alone to claim recovery from timed-out logs.

## 2026-10-23 — native/export parser parity

Extended the SGR candidate to the standalone exported pytest parser as a separate minimal patch. Leaving it native-only would allow discovery to recognize colored statuses while exported grading still misreads them. Verified exact upstream standalone source hash, and exercised all 12 expected-status cases in both native and exported parser variants. Plain-output baseline parity and colored candidate parity pass; no test IDs are renamed. Completion remains a separate gate and no historical task was regraded. Resources are recorded in `parser-export-resources.txt`; no model/remote calls or temporary inputs were needed.
