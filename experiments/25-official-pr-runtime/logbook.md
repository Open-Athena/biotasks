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

Installation check submission succeeded at 2026-10-20 19:47:21 UTC. The local
launcher used 218,328 KiB peak RSS and exited zero; Iris client checkout was
`24aa43cea9a508449d4c9094cb3877e6e43e0f67`. A first observation reported
`PENDING`. The later observation attempt at approximately 19:50 UTC could not
acquire the shared VM heavy-work lock and did not start. No resubmission was
made. Terminal state, archived outputs and remote cleanup remain unverified;
inspect the existing job before any further execution. Its scheduling timeout
is 180 seconds and execution timeout is 1,800 seconds. It carries no credentials
and cannot make model calls. Local launcher and observation processes exited;
no local worker remains owned by this task.

At 19:58 UTC, a direct lightweight observation confirmed install-001 was
UNSCHEDULABLE with no attempts and no output archive. The pinned worker was
absent from the current worker list. This is an infrastructure placement failure,
not an installation or pipeline result. The next submission prefers an occupied
existing reserved host and checks reported resource headroom before pinning it.
No repository bootstrap or model-call retry is involved. Lightweight remote
status reads do not require the local heavy-work lock; the previous lock gate
was unnecessarily restrictive.

The second installation check completed successfully in approximately 33 seconds.
The archive checksum and size were verified on readback. Upstream 0.9.3, Harbor
0.22.0, GitHub CLI 2.97.0 and Python 3.12.15 loaded; all five native configs passed.
Two containers were inspected at 1.5 CPUs/6 GiB each; a third was rejected. No
owned containers remained. Docker 23.0.6 client matched daemon API 1.42. Evidence
is under `install-002/`. There were no model calls or repository bootstraps.

The persistent runner reuses that setup and pins its observed base-image digest
and Docker archive checksum. It receives the authorized OpenRouter key only via
process environment; repository containers do not receive it. GitHub login stays
inside the private controller. Native execution requires a checkpointed command
and an explicit go file delivered through Iris's supported `task exec` interface.
The runner has a ten-hour total timeout (40 allocated CPU-hours maximum), no
retries, and the same four-CPU/16-GiB reservation and container caps. Installation,
authentication and waiting time count against that ceiling. The prior check used
about 0.04 allocated CPU-hours. Authentication is limited to fifteen minutes and
waiting for the native command to one hour. Only run-owned resources are cleaned.

Persistent job `/exedev/biotasks25-official-001` started successfully; the user
completed device login, and the runner emitted AUTH_READY. The checkpointed
native orchestration invokes `repo2rlenv --no-ui generate --config ...
--max-spend-usd 5` in the recorded five-window order. A second window for a
repository requires a native cache record and its local image; otherwise it is
left unresolved, without another bootstrap. Each native return code and log is
preserved. Generation failures are not repaired. If exports exist, the controller
keeps their images alive for up to two hours for separately checkpointed official
base/reference grading, within its original total deadline. If no exports exist,
there are no grading inputs. The archive includes native caches and outputs only,
never the controller's GitHub authentication directory.

### 2026-10-20 — native result and final evidence

The persistent run completed without intervention in repository environments.
Scikit-fingerprints and PsychoPy each exhausted twenty native agent turns; their
later windows were skipped rather than re-bootstrapped. Nipype saved an environment
in nine turns and passed upstream's fresh-image gate (which accepted test exit 1),
then selected six PRs. Four lacked test patches; #3755 and comparison #3753 yielded
zero parsed pre/post tests and were rejected. There were no exports, hence no
base/reference grading inputs. Native validation output for rejected PRs was not
persisted by upstream; its precise zero-parsed-test cause remains unverified.

All five jobs are terminal. The original 27,016-byte archive was downloaded and
verified against its authoritative checksum; native cache/output payloads were
extracted with path/type/size bounds. The supervisor recorded zero remaining owned
containers, controllers and images. Small original records and source notices are
retained in Git so the temporary seven-day object is not the only copy. Textual
inputs and extracted artifacts passed a credential scan, including comparison
against the authorized OpenRouter key without printing or copying its value.

Final attempt-based compute accounting is 1.5063416667 allocated CPU-hours. This
uses attempt timestamps consistently and supersedes the earlier preflight-only
job-interval total without deleting that observation. Model billing, request IDs,
token usage and resolved provider are unavailable from the native records. All
cost estimates were zero; the configured estimated-dollar guard therefore did not
provide a billing bound. There were 49 agent iterations, 17 INVALID actions, and
48 transcript entries because successful SAVE_SETUP is omitted from the transcript.
Retained invalid prefixes demonstrate newline/format mismatches; no extra model
call or corrective rerun was made. See results.md for the configuration-specific
negative conclusion and reproducibility limits.
