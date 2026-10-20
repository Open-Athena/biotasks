# Official PR-runtime evaluation

## 2026-10-20 — Preparation

Research branch starts at main commit
`2a1950d239f1ada467c35393991dac87debe35f7`.
Issue: https://github.com/Open-Athena/biotasks/issues/25.

The baseline source under inspection is upstream commit
`27d04ee8203cd5b2f20c3997d13836e5f5b64238`, matching #24.
No upstream modifications, remote jobs or model calls have been made for #25.

The user approved Sonnet 4.6 through OpenRouter with a $5 estimated stop
threshold per repository, three repositories, and at most 20 bootstrap turns
each. The user then asked whether that model was current. Anthropic's live
Sonnet page lists Sonnet 5.5 (September 28, 2026). Model selection is pending
the user's response to switching to 5.5 with the same limits; do not launch
the approved older model while this question is pending.

Source findings:

- The official `generate` command invokes `ensure_bootstrap` and then the
  native pipeline. It supports model/provider configuration, a spending
  threshold, and bootstrap options. Use configuration files for typed limits.
- The bootstrap agent checks estimated spending between calls, with 2,048
  output tokens requested per call. A final call can exceed the threshold.
  The LLM wrapper catches cost-estimation errors and returns zero, so the
  dollar threshold is not a hard billing cap or a guaranteed accounting bound.
- The native GitHub PR selector supports count and merge-date bounds, not an
  explicit PR-number allowlist. It fetches up to min(limit * 3, 1000) recent
  merged PRs and then filters dates locally. The five previously inspected
  inputs may require a documented broader comparison cohort; do not modify
  the selector or impersonate GitHub responses to force membership.
- Remote GitHub authentication needs an authorized credential or an official
  execution arrangement. Local normal elevated `gh` works, but no GH_TOKEN or
  GITHUB_TOKEN is present in this process. Do not extract credentials from
  helpers or repurpose local authentication stores.

### Model selection superseded

The user selected the existing free GLM-5.3 service instead of either Sonnet
version or OpenRouter. Use the approved bulk service route and credential;
no paid fallback. Retain at most 20 bootstrap turns per repository. The
upstream agent requests at most 2,048 output tokens per call, so three
20-turn bootstrap invocations request at most 122,880 output tokens in
aggregate; input tokens and wall-clock time must also be recorded.

The official `LLMSpec` supports provider `openai`, model `glm-5.3`, a custom
endpoint and an explicit credential environment variable. This needs no
source modification. Runtime compatibility is not yet demonstrated. Keep
service endpoints and access details private. The documented service route
is on CoreWeave; connectivity from reserved TRC workers is not established.
Read-only discovery must precede a launch. Do not bypass the approved relay
or provision new capacity to bridge the route.

Next: inspect official selection coverage and
remote prerequisites, freeze a concrete invocation and resource accounting,
then run without an external repair stage.

### Selection and connectivity preflight

Read-only live GitHub listing confirms the five target merge-date windows
include 16 PRs before native filtering: the five comparison inputs and 11
additional same-day PRs. Preserve upstream selection and report those
additional inputs separately. `selection-preflight.json` records membership.

Two bounded, zero-generation connectivity jobs ran on existing reserved TRC
CPUs. The first failed before the probe because its worker did not support
the requested sandbox-profile enum. The second used the supported restricted
profile on a known compatible worker and completed, reporting a `URLError`
after approximately ten seconds when requesting the approved relay's
models route without credentials. No HTTP response was observed; service
authentication and generation were not tested. Both jobs are terminal.
The result does not establish a global GLM outage. No pipeline run occurred.

Current access documentation describes the GLM relay for callers inside its
serving cluster. A supported reachable route from TRC is still needed.
Remote GitHub authentication is also unresolved. Inspected concrete upstream
and Marin authentication precedents are in `authentication-options.md`.
No credentials were extracted from the local CLI or other stores.

Native DockerSandbox starts sibling containers without CPU/memory flags.
The outer Iris job allocation therefore does not itself establish the
promised resource bound for those containers. A bounded execution arrangement
must be documented and agreed before a pipeline launch; no source patch or
Docker interception has been applied.

### CoreWeave execution check

At the user's request, inspected the configured CoreWeave CPU pool and Iris
Kubernetes execution backend. The configuration specifies existing always-warm
CPU capacity; this is not a measurement of currently free schedulable CPUs.
The approved GLM access documentation describes in-cluster relay discovery.

`lib/iris/src/iris/cluster/backends/k8s/tasks.py::_security_context`
explicitly rejects `DOCKER_ACCESS`: these nodes use containerd rather than
a host Docker daemon. The source names `PRIVILEGED` with an in-pod runtime
as an alternative and maps that profile to Kubernetes privileged mode.
Therefore CoreWeave is not a ready-made host-Docker executor. A bounded
Docker-in-Docker pod is a possible infrastructure arrangement, not a verified
working setup. It would leave Repo2RLEnv source unchanged, but its privileged
execution must be explicitly authorized and supported by cluster policy.
No privileged pod, daemon, model call or new capacity was launched.

### OpenRouter model choice

The user approved GLM-5.3 through OpenRouter after discussing cost and reliability. This supersedes the private free-service route and removes that network requirement from the intended TRC run. Keep the previously approved $5 estimated stop threshold per repository, 20 turns and no model fallback. Public endpoint metadata confirms support for the native temperature and max_tokens parameters; this is not a live generation check. The fixed 2,048-token output budget may constrain always-on reasoning. No upstream patch, extra generation probe or model call was made. Prices vary by routed provider; the quoted starting price is not a guaranteed per-run price.

### 2026-10-20 — approved resource wrapper and installation gate

The user approved the resource-only Docker wrapper. It preserves upstream source
and arguments except for container CPU/memory/network caps and ownership labels.
Syntax and pure argument checks passed locally. A separate bounded, credential-free
TRC installation check will install the pinned official archive with its frozen
lockfile and Harbor extra, validate all five native configs, and exercise two
container slots plus rejection of a third. It makes no model calls and performs
no target-repository bootstrap or repairs. The check uses Docker CLI 23.0.6,
uv 0.11.31, GitHub CLI 2.97.0, and records the resolved Python controller image.
Native generation remains unlaunched until this infrastructure gate passes.
