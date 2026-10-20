# Runtime evaluation plan

Status: cohort membership is frozen; runtime configuration is still in development.
No candidate PR has been executed in this experiment.

The question is whether native Repo2RLEnv `pr_runtime` can generate useful tasks
without per-PR human intervention. The baseline is upstream commit
`27d04ee8203cd5b2f20c3997d13836e5f5b64238`, with its unchanged validation and
export path. An alternate execution backend must be reported separately; a
successful Python test run alone does not establish native Docker task validity.

## Inputs and development boundary

`execution-cohorts.json` records four development PRs and twelve held-out PRs,
including two PRs from a repository absent from development. Membership is
derived from the static scan using a fixed seed. This is a small feasibility
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

Keep native rejection, environment failure, additional quality rejection,
accepted export, and independently verified task as separate states. Report
counts over the initial 115 sampled PRs, the 16 statically eligible PRs, and the
12 held-out execution inputs, with development results separate.

## Proposed decision gates and bounds

Freeze these gates before held-out execution. A promising result requires at
least four independently verified tasks among the twelve held-out inputs,
covering at least two repositories, with no audited false acceptance. Report
the unseen-repository result separately even if it fails. This pilot cannot
establish a low population-wide false-acceptance rate.

Proposed execution ceilings are two concurrent CPU workers on existing reserved
TRC capacity, each at most four CPUs, 16 GiB RAM and 30 GiB disk; one hour per
repository bootstrap; thirty minutes per PR validation and final verification;
and 48 allocated CPU-hours total. Scheduling time is recorded separately.
Do not purchase capacity or request accelerators. Start at one worker.
These are ceilings, not measured costs or proof of scheduler capacity.

Use zero paid model calls until a model budget and provider are recorded.
Supplied Dockerfiles are allowed by upstream, but their authorship effort and
repository-specific assumptions must be counted; they do not prove automated
bootstrap for unseen repositories. A model-assisted bootstrap requires a
separately checkpointed call/token ceiling and provider configuration.

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
