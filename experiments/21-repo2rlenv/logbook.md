# Repo2RLEnv cross-language experiment

## 2026-10-16 — preparation

- Published issue #21 and verified the exact body and agent-generated label.
- Started codex/research/21-repo2rlenv from main at 2a1950d239f1ada467c35393991dac87debe35f7.
- Pinned Repo2RLEnv, four biological source repositories, and Marin in source-manifest.json.
- Inventoried 23 executable routes plus planned SEC-bench in applicability.csv. These are static assessments, not execution results. No model calls, generation, biological execution, or workers launched.
- The non-Python panel exposes a real gap: native runtime log dispatch has no R/testthat or bedtools shell-test parser. C++ bootstrap support alone cannot establish test-based task generation. Preserve unmodified baseline blockers before considering adapters.
- Biopython uses Tests/run_tests.py, a custom PyUnit runner with offline selection; scikit-bio keeps tests under skbio. Explicit source/test profiles are needed rather than assuming a root tests directory. Parser compatibility is untested.
- Tasksmith requires an Anthropic author. CodeMidas documents dedicated Sol/Luna stages; its GLM substitution remains unresolved. Neither is authorized to fall back to paid models.
- Native equivalence_tests exposes its reference in the learner image. Record generation separately from isolation acceptance.

Next: inspect dedicated model paths and cap semantics, select bounded historical candidates, prepare Python profiles, and fix the worker/backend and aggregate execution ceilings. Budget fields left null are unresolved, not unlimited. Seed routes need separately frozen cohorts. Any billable worker launch requires an agreed allowance.

### Bounded PR discovery

Recorded ten merged PR locators per repository in pr-discovery.json (40 total), using the CLI default updated ordering. These are discovery records, not 40 generation attempts. Titles suggest useful leads: Biopython #5344 (alignment score), scikit-bio #2630 (sequence case conversion), bedtools #999 (genome-file line endings), and DESeq2 #118 (greaterAbs with useT). Source/test diffs, historical environments, and exact execution base/head commits remain to inspect. Documentation-only and maintenance changes stay in the discovery ledger rather than disappearing from the denominator.
