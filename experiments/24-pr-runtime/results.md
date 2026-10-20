# PR-runtime feasibility results

**Decision: no-go for promoting this configuration into an operational
pipeline.** The five-input recovery produced zero technically qualifying
candidates: three native rejections and two bootstrap-unresolved inputs.
The technical upper bound alone misses the frozen four-task/two-repository
gate. There is no task release or pipeline PR.

## Source opportunity

The inventory contains 1,014 source identities and 952 historical GitHub
repository names. Resolution yields 951 live repositories and one unresolved
repository. Of these, 871 are primary source mappings; 143 source identities
remain unmapped. Primary mappings and additional linked repositories are
different populations.

In the fixed 2025-10-20 through 2026-10-19 window, the 951 live repositories
have 48,196 merged PRs. The 871 primary repositories have 47,107; 509 are active
in the window. These are observed PR counts, not task counts.

The reproducible 12-repository panel contains 115 inspected PRs and 16 native
statically eligible candidates: 10 scikit-fingerprints, four Nipype and two
PsychoPy. The panel varies language and activity, but is not a representative
sample of all 47,107 primary-repository PRs. No population-wide executable
yield is estimated.

| Repository | Window PRs | Inspected | Static candidates | Within-repository estimated candidates, approximate 95% interval |
| --- | ---: | ---: | ---: | --- |
| MLCIL/scikit-fingerprints | 111 | 20 | 10 | 55.5 (33.2–77.8) |
| nipy/nipype | 27 | 20 | 4 | 5.4 (2.2–11.2) |
| psychopy/psychopy | 315 | 20 | 2 | 31.5 (8.8–113.5) |

The other nine panel repositories produced no static admissions. That is not
proof of zero opportunity: for example, the native new-test-function heuristic
misses R `test_that` tests. The evaluated execution profile is specifically
Python/pyproject; unsupported profiles must not be read as scientific
rejections. Full counts, dispositions and interval methods are in
`inventory/opportunity-summary.json`.

One PsychoPy binary-fixture diff retains its original unresolved completeness
disposition because the native header regex misses paths containing spaces.
A separate diagnosis identifies fixture-only changes; it does not overwrite
the original scan. The reported candidate interval includes that uncertainty.

The 16 candidates form eight conservative shared-file/reference overlap
components. Components are not proven semantic fix families. Seven original
held-out slots were excluded for development overlap, without replacements.
Four PRs are development inputs and five remain held out; two are from the
unseen PsychoPy repository. The go target stayed at four verified tasks across
two repositories out of the twelve original held-out slots.

## Baseline and development

The native source is Repo2RLEnv
`27d04ee8203cd5b2f20c3997d13836e5f5b64238`. Its supplied-Dockerfile bootstrap
returns empty test commands; the unchanged validator rejects that metadata.
This was exercised as a separate empty-command control. Native model-assisted
bootstrap was not evaluated.

The tested adaptation installs declared Python build/test dependencies,
discovers editable-backend requirements, and rebuilds editable metadata after
native reset/clean. It uses Python 3.12, a digest-pinned base image and pinned
runner dependencies. Target package versions are recorded after bootstrap;
package-index contents and wheels are not archived.

Ten development jobs, including failed attempts, consumed 1.549077 allocated
CPU-hours. Both Nipype PRs eventually passed native validation:

| Development PR | F2P | P2P | Export/control evidence |
| --- | ---: | ---: | --- |
| Nipype #3745 | 2 | 3 | Native image built; base/test deletion fail; reference passes; omitted source portions score 0 or 0.5, never full reward |
| Nipype #3766 | 1 | 17 | Native image built; base, omitted source and test deletion fail; reference passes |

Scikit-fingerprints #652 and #649 passed 12 and three reference tests,
respectively, but their base stages failed collection because the new modules
did not exist. Native per-test identity matching found no F2P transitions.
These are feature-addition limitations, not evidence of missing external
dependencies.

Development fixes addressed executable tools on an Iris `noexec` mount,
generated version metadata deleted by native cleanup, dynamic editable-build
requirements, Python-version compatibility, Docker commit transport, and extra
gate parsing. They changed no target source or tests. Active engineering time
was not instrumented; the dated logbook and all attempts preserve the setup
effort rather than treating it as free.

Nine synthetic native-verifier cases show that native reward alone can accept
unparsed output or incomplete/untracked failures. The additional gates require
tracked test success and clean command completion. Eight regression cases
check the extra-gate treatment of application ERROR logs, actual test errors
and fractional partial-solution rewards.

## Frozen campaign and infrastructure recoveries

The original freeze is commit `1f087934`, with `freeze.md` and
`heldout-campaign.json`. It failed unattended completion: both submitted jobs
were lost to the same worker reconciliation failure, with no logs or output
archives. Three PR inputs were assigned but have no observable validation
outcome; two PsychoPy inputs were not submitted. The launcher omitted
`WORKER_FAILED` from terminal states and was explicitly stopped. These are
infrastructure-unresolved inputs, not failed regression tasks. Cleanup on the
lost worker could not be independently verified.

A separately recorded recovery used Iris's canonical terminal-state predicate
and preserved all terminal failures. Its historical-worker allowlist preflight
submitted no jobs because those workers were no longer eligible. The next
selection used currently healthy reserved workers; all three jobs landed on
worker build `68f0ea2078`, which lacks the required `iris-egress` network.
They failed before repository setup, and all archives and cleanup reports were
verified.

Live provenance inspection found 52 older workers and 132 at clean build
`205558e1a7` / tree `46a4bef234`, whose Docker runtime supports the declared
network. Version v3 requires that worker build. No host firewall/network
configuration or cluster changes were made.

All recovery versions retain the exact original PRs, worker code, bootstrap
algorithm, dependencies, native validator/exporter/grader, and acceptance
rules. Only infrastructure orchestration, scheduling and run identities
change. Earlier failures remain in both outcomes and cost. These are
same-cohort recoveries, not independent fresh-cohort estimates or retroactive
successes for the original campaign.

## Runtime outcomes and separate audit

Capability-aware v3 completed from one entry point with verified output
archives and owned-container/image cleanup for all three repository jobs.
No PR-specific environment, source, test, instruction or grader repair was
applied. The worker and dependency-code hashes and all candidate inputs are
unchanged from the original freeze, apart from run identity/provenance.

| Held-out input | Observed outcome | F2P / P2P | Disposition |
| --- | --- | --- | --- |
| scikit-fingerprints #544 | Base: zero collected, missing new `skfp.datasets.asap` module. Reference: 34 passed. | 0 / 0 | Native rejection: no per-test F2P transition |
| scikit-fingerprints #525 | All eight tests, including the added chirality test, pass before and after the fix. | 0 / 8 | Native rejection: no failing baseline in this environment |
| Nipype #3753 | Base: zero collected, 30 relative-import collection errors. Reference: 54 passed, one skipped. | 0 / 0 | Native rejection: new-interface collection failure |
| PsychoPy #7475 | Shared repository bootstrap failed before PR validation. | Not reached | Bootstrap unresolved |
| PsychoPy #7805 | Same shared bootstrap failure; no replacement or repair. | Not reached | Bootstrap unresolved |

PsychoPy's observed failure is specifically a transitive wxPython source
dependency that cannot import `setuptools.build_meta` while the generic
installer uses `--no-build-isolation`. It is not an observed graphics/test
failure, nor evidence that either PR is invalid.

Configured-repository validation reached all three selected PRs, with zero
native admissions. Onboarding the unseen repository failed before validating
its two PRs. There are zero qualifying outputs among the five execution inputs
and twelve original held-out slots, and zero accepted fix families. Seven
overlap exclusions and four development inputs remain separate; this is not a
0/115 population acceptance estimate.

All five nonaccepted inputs received a separate source/log review, covering
the preselected hash-ranked subset. The three native rejections agree with
the declared gates. In particular, the new chirality test is explicitly
`PASSED` in both logs. This does not prove the upstream fix is unnecessary:
the test, current resolved dependencies, or both may explain the absent
regression. Historical dependency behavior was not reconstructed.

No accepted-output false-acceptance rate can be estimated, and the broader
false-rejection rate is unknown without an independently established runnable
task set. Source review does not rescue the two setup-unresolved inputs.
The chirality description also exposes the fix approach; the MovieStim test
has graphics/fixture and retained-coverage concerns. These are separate
quality observations, not post-hoc pipeline decisions.

`evidence/final-outcomes.json` records the cases, denominators, audit membership
and unchanged-input checks. `evidence/source-audit.json` contains the source
review; raw pre/post logs and the PsychoPy installation failure are preserved
under `evidence/heldout-recovery-v3/`.

## Cost, completion and decision

| Phase | Recorded allocated CPU-hours |
| --- | ---: |
| Capability probes | 0.018149 |
| Ten development jobs, including failures | 1.549077 |
| Original worker-failed campaign | 0.148233 |
| Recovery v2, incompatible worker network | 0.139842 |
| Capability-aware recovery v3 | 0.365675 |
| **Total** | **2.220976** |

These are scheduler attempt intervals multiplied by reserved CPUs, including
unused reservation; they are not actual CPU utilization or a monetary bill.
The total is below the 48 CPU-hour ceiling. No new paid capacity or
accelerators were created, and there were zero pipeline model calls/tokens.
Interactive Codex development, active engineering time and local metadata
compute were not priced or fully instrumented. Per-accepted-task cost is
undefined because there are no accepted tasks; the recurring cost gate is not
established.

All experiment jobs are terminal. Completed recovery reports verify removal
of owned containers and images, retaining shared base caches. The original
lost-worker jobs have no recovered cleanup report; their logical terminal
states do not prove orphan cleanup. Their scheduler intervals are included,
but independent lost-worker resource accounting is unavailable.

The frozen yield gate fails even before final automatic semantic acceptance.
Retain the research evidence and do not promote this harness as a scalable
production pipeline. A future experiment would need a fresh evaluation and
explicit improvements to historical environment reproduction, meaningful
regression selection, automatic instruction/test agreement, and executor
capability/lifecycle handling. This experiment does not establish that
model-assisted Repo2RLEnv bootstrap, another language profile, or all PR-derived
task approaches are ineffective.

## Interpretation limits

The research harness records native dispositions and automatic technical
control results. It does not implement a final automatic semantic
instruction/test-agreement decision: exported records retain
`accepted=false` pending research audit. An audit must not flip that flag to
simulate unattended production acceptance. Technical control success is an
upper bound on qualifying admissions, not a completed production decision.

The single entry point covers the frozen conversion cohort; inventory
acquisition and selection remain separate reproducible research scripts.
No solver model or Harbor trial orchestrator was run. Diagnostic Docker
images are removed after verification, so task bundles with local image
references are not a reproducible task release.

Biological relevance is labeled separately from repository membership in
`evidence/biological-relevance.json`. Candidates include molecular descriptors,
dataset access, neuroimaging interfaces, adaptive psychophysics and general
runtime engineering. Unit-test fixtures and synthetic responses are not
observed biological measurements. Interface metadata tests do not establish
scientific validation on MRI data.

The source-level audit is separate from execution and makes no repairs.
It is by the same research assistant, not a blinded external reviewer.
`evidence/source-audit.json` preserves its findings, including solution leakage
in the chirality PR description and graphics/fixture requirements in MovieStim.
The joined runtime audit and final outcomes are in `evidence/final-outcomes.json`.
