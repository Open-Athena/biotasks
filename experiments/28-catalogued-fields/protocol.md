## Question

How often does unchanged official Repo2RLEnv pr_runtime produce independently verified tasks from popular, active repositories spanning the existing BioTasks scientific-field catalog? Extend the selected three-repository baseline in #27, which produced two AnnData exports and one independently verified saved task under a documented reconstructed environment. Keep #25/#26/#27 as separate baselines; do not mix their attempts into this cohort's yield.

## Cohort and selection

Reuse #5's refined scientific-field vocabulary and repository-level annotations, not notebook labels or newly invented subdomains. The source snapshot is 09e375e2dd5a2d1e055ef2e78efe778f636b9311, experiments/5-classification-pilot/full-inventory/explorer-data.json. Screen popular software within those fields using the retained discovery rankings, then refresh GitHub stars and merged-PR activity. Preserve overlapping fields, supporting scope evidence and provisional annotation status. This is a purposive cohort, not a representative sample of biology.

| Existing field | Repository | Stars at preflight | September merged PRs |
| --- | --- | ---: | ---: |
| Genomics and genetics | [samtools/samtools](https://github.com/samtools/samtools) | 1,969 | 8 |
| Transcriptomics | [scverse/scanpy](https://github.com/scverse/scanpy) | 2,592 | 24 |
| Epigenomics | [macs3-project/MACS](https://github.com/macs3-project/MACS) | 788 | 9 |
| Proteomics | [OpenMS/OpenMS](https://github.com/OpenMS/OpenMS) | 628 | 217 |
| Structural biology | [lammps/lammps](https://github.com/lammps/lammps) | 3,105 | 34 |
| Metabolomics | [matchms/matchms](https://github.com/matchms/matchms) | 276 | 11 |
| Systems biology | [opencobra/cobrapy](https://github.com/opencobra/cobrapy) | 589 | 4 |
| Microbiome science | [soedinglab/MMseqs2](https://github.com/soedinglab/MMseqs2) | 2,156 | 9 |
| Neuroscience | [mne-tools/mne-python](https://github.com/mne-tools/mne-python) | 3,559 | 82 |
| Bioimage analysis | [OHIF/Viewers](https://github.com/OHIF/Viewers) | 4,385 | 38 |

The 2026-10-22 preflight found 436 merged PRs in the common 2026-09-01 through 2026-09-30 window, before native eligibility filters. Pin each repository's default-branch revision before execution. Keep native limit=100 and upstream selection/filtering unchanged for comparison. OpenMS has 217 window merges: the native limit and newest-300 overfetch may censor its window. Independently reconcile the complete window for accounting, record which PRs upstream actually considered, and never call all 436 a completed-processing denominator. Do not handpick PRs, alter pagination or substitute repositories after seeing generation results.

## Unchanged pipeline and permitted infrastructure

Use huggingface/Repo2RLEnv@27d04ee8203cd5b2f20c3997d13836e5f5b64238, the previous pinned source, and fresh bootstrap caches per repository. Retain OpenRouter anthropic/claude-sonnet-4.6, no fallback, native temperature 0.2 and 2048 output tokens, at most 20 bootstrap iterations/1800 seconds and the existing $5 estimated per-repository threshold. Only upstream's built-in model calls are permitted, including its own bootstrap actions. Do not add a Codex/LLM repair loop, manual package/interpreter choice, modified installation recipe, extra setup prompt, test subset, source patch, parser adapter, candidate bypass or manual generation retry outside the official generation/control operations.

Use the previously approved resource/image/network/cleanup wrapper on existing reserved TRC CPU capacity. Preserve one-CPU/six-GiB Harbor controls and 1.5-CPU/six-GiB native containers; at most two native containers for upstream's fresh-image check. Allocate at most four CPUs/16 GiB per job and run repositories serially. No accelerators, new workers or new paid capacity. Infrastructure changes must be enumerated and justified before use.

Static inspection of native validation found explicit parsers for pytest/unittest, Jest-style output, Go and Rust, but no explicit CTest, standalone GoogleTest or generic shell/Perl harness. Bootstrap language recognition does not establish test-parser compatibility. Preserve the ten-repository cohort: record unsupported or unparseable output as an outcome, without adding adapters. This is a known risk, not a finding that any particular repository has already failed.

## Independent controls and timeout diagnosis

For each emitted export reached within the declared budget, run official Harbor 0.6.6 no-op/base and reference-patch oracle controls, once each, serially. Preserve the generated task files and source recipes. A verified task requires parsed test evidence, base reward 0 and oracle reward 1; report strict oracle command resolution, P2P regressions, skips, untracked failures and parse fallbacks separately. A timeout has no reward unless a verifier actually writes one; never equate it with reward zero.

Give primary controls an execution budget separate from bootstrap/generation so generation cannot consume their time. Keep the original 300-second task verifier limit for the baseline comparison. Harbor -r 0 disables trial retries but retains its built-in single verifier-timeout retry; record both attempts. Stop between complete trials where possible, and label any deadline-censored or unstarted controls explicitly.

A proposed diagnostic for timeout-affected exports is a second, separately reported base/oracle pair with Harbor's supported --verifier-timeout-multiplier 6 (1800 seconds per attempt), preserving CPU/memory, task bytes and commands. Run it only under a separate explicit budget; it cannot upgrade the primary 300-second result. This is a declared time-budget comparison, not a task or environment repair. Do not silently regenerate or fix the export.

## Approved serial budget and execution

Proceed with the ten-repository primary experiment on existing reserved TRC CPUs. The user approved the shared-key serial $5 stop threshold: one repository and one upstream model request at a time; stop additional model calls once that repository's recorded actual OpenRouter charges reach $5. The final request can overshoot. This replaces the proposed strict provider-side $5 ceiling; it is not a hard billing cap. Retain upstream's unchanged $5 estimated threshold as well. Stop the campaign before another repository if known cumulative actual charges reach $50, or if a dispatched request's charge cannot be resolved. Do not attribute shared whole-account usage deltas to a repository.

A minimal controller-side observer wraps upstream LiteLLM completion: forward identical arguments once, return the identical response, retain response IDs/token usage/actual cost, and perform only read-only per-generation billing lookups if the response omits actual cost. Stop future calls if actual cost remains unavailable; no extra model calls, retries, fallback, prompts or repairs are added. Record upstream candidate/filter/validation decisions and raw sandbox command outcomes to explain yield and parser/timeout behavior. Source bytes, parser behavior and task files stay unchanged. Exact credential values are excluded from saved observations.

The primary reserved allocation ceiling is 100 CPU-hours across ten serial jobs, each at four allocated CPUs for at most 150 minutes. Setup and native generation receive up to 84 minutes per repository (within the originally proposed 90); primary controls have their own full hour; five minutes are reserved for archival/cleanup, with one minute of scheduling/termination margin. Failed infrastructure and every attempt count. End early when stages complete; no automatic generation retries or replacement repositories. Native deadline-censored attempts retain their evidence, and any already emitted exports proceed to the independent control stage. Record unstarted/censored controls explicitly; do not begin another trial with less than 660 seconds left. The longer verifier-timeout diagnostic remains outside this approved primary allocation and requires a separate explicit budget.

The approved resource/image/network/cleanup wrappers remain unchanged in behavior. Controller orchestration is adapted only to this ten-repository serial cohort, the separate stage deadlines, actual-cost guard and metadata observations. Record fresh bootstrap/image provenance before owned image cleanup; archive original generated files, observations and independent trial outputs. No new model calls or repository/environment repairs are authorized.

## Evidence and conclusion

Create a fresh permanent codex/research/<issue>-<topic> branch from a recorded current main commit after filing. Checkpoint all executable inputs and exact source/repository refs before a run. Retain bootstrap flags/transcripts, actual saved test commands, native filter/skip decisions, discovered/considered/paired-validation/export counts, original task bytes, raw independent trial results, timeout diagnostics, actual cost availability, CPU allocation and owned cleanup. Preserve originals and derived summaries separately. Archive and verify readback before counting results; review source/data eligibility before public retention. Preserve a usable environment artifact or document reconstruction provenance so generation success is not confused with exact-image replay. No registry/dataset publication is included.

Report each repository's furthest completed stage and failure cause; repositories yielding at least one verified task; total verified tasks; cost per verified task and per successful repository where actual cost is available; and unresolved parser, bootstrap, transport, timeout and portability limits. Give every repository equal visibility rather than letting OpenMS dominate the pooled PR count. Repository scientific-field labels do not establish that every PR tests a biological competency. Conclude the bounded experiment even with zero exports; no supported pipeline implementation, benchmark solver run or promotion to main is included.
