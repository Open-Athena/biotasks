# Runtime evaluation plan

Status: version 2 cohort membership is recorded; runtime configuration is still in development.
No candidate PR has been executed in this experiment.

The question is whether native Repo2RLEnv `pr_runtime` can generate useful tasks
without per-PR human intervention. The baseline is upstream commit
`27d04ee8203cd5b2f20c3997d13836e5f5b64238`, with its unchanged validation and
export path. An alternate execution backend must be reported separately; a
successful Python test run alone does not establish native Docker task validity.

## Inputs and development boundary

`execution-cohorts.json` preserves the initial four development PRs and twelve
held-out slots. The pre-execution overlap audit produces
`execution-cohorts-v2.json`: four development PRs, five eligible held-out inputs,
and seven exclusions for potential development overlap, with no replacements.
Two eligible held-out PRs are from a repository absent from development.
Membership is derived from the static scan using a fixed seed and then screened
by conservative shared-file/reference components. This is a small feasibility
panel, not a representative estimate of all biological repositories.

Use the four development PRs to establish a generic invocation, bootstrap
configuration, test reporting, and artifact preservation. Record every attempt
and any manual intervention. Do not inspect held-out test failures to tune the
configuration. Before held-out execution, checkpoint the complete configuration,
source revisions, environment specification, commands, resource limits, acceptance
policy, and model settings, if any.

## Execution and acceptance

1. Bootstrap once per declared repository/revision/configuration and retain its
   image identity. Record image reuse across historical PRs explicitly.
2. Apply the native selection and validation path to every cohort member.
   Preserve native outcomes independently of additional quality checks.
3. Automatically reject infrastructure failures, incomplete test reports,
   zero collected tests, and inconsistent before/after test identities. Require
   a genuine assertion failure before the fix and a pass afterward; an import
   error or missing dependency is not sufficient evidence of a regression task.
4. Build the exported task environment and run its verifier against both the
   base implementation and the reference fix. Require base rejection and
   reference acceptance. Check that oracle and grading assets are not exposed
   as solver inputs. Export alone is not acceptance.
5. Independently audit every accepted task in this small panel for instruction
   sufficiency, answer leakage, test relevance, and grading validity. Audit
   failures count against yield; do not repair held-out tasks individually.

Preselect rejected-output audit membership by the cohort hash ranking: audit
the first three rejected held-out inputs, or all if fewer than three. Preserve
the automatic disposition and report the audit independently; a manual audit
cannot convert a rejected output into an accepted task.

`evidence/cohort-overlap-audit.json` records potential overlap using patch
identities, shared issue references, and shared source files. Eight PRs add
Mordred descriptor functionality through a shared calculator; two were in
development, so the other six are excluded. One Nipype held-out PR shares a
source file with a development PR and is conservatively excluded too. Shared
files are not proof of duplicate fixes; cross-repository semantic duplication
is not ruled out. Preserve these limitations when reporting unique fix families.

Automatic acceptance also requires a bounded set of negative controls: the
unchanged base, removal of each source-file portion of the reference patch
(up to five files, hash-ranked), and test-file deletion/tampering. Record
controls that do not apply cleanly as unresolved controls, not successful
rejections. Passing partial implementations reveal insufficient discrimination;
reject those candidates under the frozen policy. This is limited mutation
coverage, not a proof against every incorrect implementation.

Keep native rejection, environment failure, additional quality rejection,
accepted export, and independently verified task as separate states. Report
counts over the initial 115 sampled PRs, the 16 statically eligible PRs, and the
12 original held-out slots and five overlap-screened execution inputs, with
development results and the seven overlap exclusions separate.

## Proposed decision gates and bounds

Freeze these gates before held-out execution. A promising result requires at
least four independently verified tasks among the twelve original held-out slots,
covering at least two repositories, with no audited false acceptance. Report
the unseen-repository result separately even if it fails. This pilot cannot
establish a low population-wide false-acceptance rate.
The overlap screen does not reduce this absolute target or replace excluded
inputs; four accepted tasks would require four of the five remaining execution
inputs to pass. Assess feasibility during development and report failure to meet
the target honestly.

Proposed execution ceilings are two concurrent CPU workers on existing reserved
TRC capacity, each at most four CPUs, 16 GiB RAM and 30 GiB disk; one hour per
repository bootstrap; thirty minutes per PR validation and final verification;
and 48 allocated CPU-hours total. Scheduling time is recorded separately.
Do not purchase capacity or request accelerators. Start at one worker.
These are ceilings, not measured costs or proof of scheduler capacity.
The proposed recurring compute gate is at most 12 allocated CPU-hours per
independently verified held-out task, including failed held-out attempts and
amortized bootstrap cost. Report development engineering time separately.

Use zero paid model calls until a model budget and provider are recorded.
Supplied Dockerfiles are allowed by upstream, but their authorship effort and
repository-specific assumptions must be counted; they do not prove automated
bootstrap for unseen repositories. A model-assisted bootstrap requires a
separately checkpointed call/token ceiling and provider configuration.

At this pinned revision, the supplied-Dockerfile bootstrap returns empty
`test_cmds`, unknown language, and `smoke_passed=True` without a smoke run.
The native runtime validator immediately rejects empty test commands.
Consequently a supplied Dockerfile alone is not an executable model-free
`pr_runtime` profile. A declarative test-command/language configuration and
an actual fresh-container smoke check would be an explicit improved variant,
with its engineering cost and behavior measured separately from native results.

If promising, the operational follow-through must demonstrate repeatable
invocation, resumption without duplicate work, bounded retries, automatic
rejection, and durable artifact readback. Promote supported changes separately
from this research branch. Otherwise report which gate failed and what the
evidence supports, without declaring static candidates runnable.

## Current execution boundary

An Iris SANDBOX CPU probe succeeded on existing reserved TRC capacity with
public package-index access and no host Docker socket. Native Docker daemon
compatibility has not been demonstrated. The prepared DOCKER_ACCESS probe was
rejected by automatic approval review because the profile grants
host-root-equivalent access. The user's follow-up asked for an explanation,
not authorization. Do not submit that probe or an equivalent host-access route
without authorization. Do not alter shared hosts or cluster configuration.

Daytona has not been prepared or launched for this experiment, and previous
experiments' paid allowances do not apply.

## Native verifier audit

`audit_native_verifier.py` executes the hash-pinned standalone native verifier
on nine synthetic logs. `evidence/native-verifier-audit.json` preserves inputs
and outputs. Native reward can equal one for unparseable output, untracked
failures, or a failing command; these rewards do not prove task acceptance.
Even `command_resolved` does not reject an untracked ERROR if the supplied exit
code is zero. Require parsed per-test evidence, tracked-test success, clean
command completion, no FAILED/ERROR statuses, and nonempty retained regression
coverage in the additional reference gate. These checks do not establish
baseline validity, honest log provenance, or semantic agreement on their own.
Any change to the exported reward implementation is a declared improved variant,
not an unchanged native baseline.
