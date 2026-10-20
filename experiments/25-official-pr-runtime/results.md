# Official Repo2RLEnv PR-runtime result

The pinned official pipeline ran with unchanged upstream source and the approved
Docker resource wrapper, but produced **zero tasks**. This configuration is not
ready for a scalable unattended task-production pipeline. This is a completed
negative comparison, not a conclusion that PR-derived tasks or Repo2RLEnv cannot
work with other models, budgets, inputs or native improvements.

## Native outcomes

| Repository | Bootstrap | Native PR processing | Exports |
| --- | --- | --- | --- |
| scikit-fingerprints | Hit 20-turn limit; 11 invalid actions | Not reached; second window skipped without retrying bootstrap | 0 |
| Nipype | Saved setup after 9 turns; native fresh-image check accepted it | 6 candidates: 4 without test patches, 2 rejected with zero parsed tests before and after the fix | 0 |
| PsychoPy | Hit 20-turn limit; 5 invalid actions | Not reached; second window skipped without retrying bootstrap | 0 |

There were three native CLI invocations and two deliberately unrun later windows.
The 16 PRs covered by the preflight date windows were **not** all selected or
executed by the native pipeline: only Nipype reached selection, and only two of
its six candidates reached validation. No `task.toml` was exported. Base/reference
grading therefore had no inputs and did not run; there are no verified tasks.
The supervisor job succeeded because orchestration and cleanup completed; each
native CLI invocation returned 1. Job success is not task-generation success.

[Structured outcomes](evidence/final-outcomes.json) retain all 16 planned PRs,
separating the five comparison inputs from 11 additional same-day PRs.

## What failed, and what remains unknown

**Action-format compatibility consumed the native agent budget.** Across 49
agent iterations, 17 responses were marked `INVALID`: 11 for scikit-fingerprints,
one for Nipype and five for PsychoPy. Retained examples concatenate
`Thought: ...Action: BASH` on one line. The pinned parser requires a newline before
`Action:` and `Input:`. This is a concrete mismatch between this model's responses
and the native text-action protocol. It was not repaired. The native transcript
contains 48 entries because the successful terminal `SAVE_SETUP` turn is omitted;
Nipype's bootstrap record and CLI log establish its nine iterations. Raw complete
responses and finish reasons were not retained, so output-token truncation is not
established as the cause.

**scikit-fingerprints did not finish dependency/test preparation.** Its retained
last observation includes collection import errors for missing `requests` and
`torch`. It exhausted the 20-turn limit without saving a setup. Eleven format
errors left only nine executable shell actions. This does not prove that the
repository is intrinsically uninstallable.

**PsychoPy encountered a Python-version mismatch and dependency resolution/build
failures.** The native agent detected the project's `<3.12` requirement against
its automatically chosen Python 3.12 base and created a Python 3.11 environment.
Later retained output shows resolution to SciPy 1.6.1 and a source-build failure
because BLAS/LAPACK libraries were unavailable. It reached the turn limit without
saving a setup. All installation decisions and attempted repairs here were made
by upstream's built-in agent, not by an external installer or Codex repair stage.

**Nipype's bootstrap acceptance did not establish a useful PR oracle.** Its fresh
image has `verify_passed=true`, but `verify_detail` records test exit code 1.
Upstream accepts tests executing with failures at this stage; that is not an
all-tests-pass claim. PRs #3755 and comparison input #3753 subsequently produced
zero parsed pre-fix and post-fix tests, and were rejected as `no_fail_to_pass`.
The native rejection path does not persist the raw validation outputs, and these
plain CLI logs do not explain why parsing found zero tests. The precise cause
remains unverified; this must not be reported as evidence that the fixes have no
behavioral effect. No diagnostic rerun or test repair was substituted for these
results. The four other selected PRs (#3765, #3759, #3751, #3722) had no test patch.
The per-PR attribution combines native aggregate outcomes/base SHAs with public
PR file metadata, rather than claiming that the plain logs enumerate all skips.

**The model cost estimator was not usable.** Every native cost estimate was zero,
although this was a paid OpenRouter route. The $5 estimated threshold per
repository therefore was not an effective billing bound. The 20-turn limits were
respected. Native records do not retain request IDs, token usage, billed costs or
the resolved OpenRouter provider; actual model spend and exact HTTP request count
including SDK retries are unavailable. Do not interpret zero estimates as free
execution or claim a measured quality/price advantage.

## Comparison with the five inputs from #24

| Comparison input | #24 custom deterministic bootstrap | #25 official model-assisted pipeline |
| --- | --- | --- |
| scikit-fingerprints #544 | Native validation rejected: no F2P | Shared bootstrap exhausted its turn limit |
| scikit-fingerprints #525 | Native validation rejected: no F2P (8 P2P tests) | Later window not run after shared bootstrap failure |
| Nipype #3753 | Native validation rejected: no F2P | Native validation rejected; zero parsed pre/post tests |
| PsychoPy #7475 | Bootstrap unresolved at wxPython build dependency | Native bootstrap exhausted its turn limit after Python/SciPy preparation failures |
| PsychoPy #7805 | Shared bootstrap unresolved | Later window not run after shared bootstrap failure |

Both experiments produced zero qualifying tasks on these comparison inputs.
This evaluates complete configurations; it does not isolate bootstrap as the
only causal difference. These are previously inspected examples, not a fresh or
representative cohort, and their counts do not estimate population-wide yield.
The immutable #24 baseline is recorded in
[evidence/baseline-24-outcomes.json](evidence/baseline-24-outcomes.json), from
`f0a955d736626ca40e527c180f70dd9169df0d55`.

## Execution and adaptations

- Upstream: `huggingface/Repo2RLEnv@27d04ee8203cd5b2f20c3997d13836e5f5b64238`;
  archive SHA-256 `9c09729e909766366d8761e71a3585a64f656d1d3c64909b0656a0af28b402e9`.
  Native invocation and orchestration were checkpointed at `8c67bf99` before calls.
- Installed upstream with `uv sync --frozen --no-dev --extra harbor`, using uv
  0.11.31, Python 3.12.15 and Harbor 0.22.0. Controller package versions are in
  the installation logs. No upstream files were patched or monkeypatched.
- Model: `openrouter/z-ai/glm-5.3`, no fallback, native temperature 0.2 and
  2,048-output-token setting; 20 bootstrap iterations and 1,800 seconds per
  repository, with native between-turn checks and a $5 estimated threshold.
  Native command/API calls can extend past a between-turn timeout check.
- Used the official five date windows at limit 1,000 because upstream cannot
  express the exact five-PR allowlist. The comparison and extra inputs are
  recorded separately. Pinned bootstrap refs and every configuration are in
  [launch-plan.json](launch-plan.json) and [proposed-configs](proposed-configs/).
- One reserved TRC worker, four CPUs/16 GiB reserved. Controller: one CPU/4 GiB.
  Approved Docker CLI wrapper: at most two owned containers, each 1.5 CPUs/6 GiB,
  no additional swap, existing `iris-egress` network, ownership labels. Native
  container limits were checked live. Caps/network can affect outcomes and are
  part of this configuration. Shared Docker daemon/cache overhead is not included
  in these container limits or measured as task memory.
- Used Docker client 23.0.6 with daemon 23.0.5/API 1.42, avoiding #24's custom
  commit-transport adaptation. GitHub CLI 2.97.0 used a fresh user-authorized
  device login in the private controller. Native `auth.use_gh_cli=false` prevented
  upstream token extraction; normal `gh` commands used their own login. The
  OpenRouter key was injected through process environment, never target-container
  arguments or public artifacts.
- The controller used a digest-pinned Python image. Native target dependencies
  were chosen by upstream's agent; a complete frozen dependency inventory for
  those target environments was not emitted. The saved Nipype image identity,
  setup commands and reconstructed Dockerfile are retained, but the image itself
  was removed during cleanup. Failed bootstrap image digests and a complete
  target dependency inventory are unavailable from native failure records.
  These are reproducibility limits, not missing
  evidence filled in by an external repair stage.

The initial private-service probes failed before generation (unsupported worker
profile, then an unreachable route). The first installation submission timed out with zero
attempts; its pinned worker was absent when subsequently inspected. The next installation check passed.
These infrastructure attempts remain separate from native scientific outcomes.
The persistent runner subsequently completed once, without manual per-input
repairs or bootstrap retries. Credential login and placement recovery were manual
infrastructure setup; this experiment did not demonstrate production credential
provisioning or scheduling automation.

## Cost, evidence and cleanup

All five #25 jobs are terminal. Final attempt-based accounting is **1.506342
allocated CPU-hours**, including probes, installation, authentication waiting,
native execution and artifact upload. This is reserved CPUs times attempt
intervals, not actual utilization. The earlier preflight note used job-level
intervals; [final lifecycle accounting](evidence/lifecycle.json) uses one consistent
attempt-based definition and does not add the old totals again. Interactive Codex
cost and engineering time are unmeasured. Billed model cost is unavailable, and
cost per accepted task is undefined because none were accepted.

The original 27,016-byte Iris archive passed SHA-256 readback verification:
`b825ff2655ebbbd04753264cf0ef2e7a3c72f1b55b7e6fc78bc0cd01ed97bb3b`.
The original archive, extracted logs, native bootstrap records, transcripts and
source-license notices are small and retained on this permanent research branch;
the temporary seven-day Iris copy is not the sole evidence store. Public evidence
excludes GitHub authentication files, device-login logs, environment dumps and
credentials. Excerpts retain their original project terms; see [licenses](licenses/).
No biological dataset or executable task release is being published.

The supervisor recorded no remaining owned task containers, controller containers
or images. The earlier installation check also verified its cleanup; the
unschedulable submission had no execution attempt. No local workload was left
running. See [archive/readback record](evidence/archive-readback.json),
[artifact manifest](artifact-manifest.json), and [verification](verification.json).

## Implication for an automated pipeline

Do not scale this exact configuration yet. The evidence supports addressing three
specific gaps before a fresh yield study: reliable native action formatting for
the selected model, usable billing/usage accounting, and preservation plus clear
classification of zero-parsed-test validation failures. Dependency preparation
also needs to succeed within an explicit budget. These are follow-up changes to
justify and test, not fixes applied to this baseline. A different model or budget
may help, but this experiment did not compare alternatives or establish that it
would solve the failures. There is no supported production pipeline change to
promote from this run.
