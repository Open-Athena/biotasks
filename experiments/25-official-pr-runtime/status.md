# Execution prerequisites unresolved

This is preflight evidence, not a Repo2RLEnv result. Issue #25 remains open.
No official generation run, model call, task export or grader execution has
occurred. No upstream source has been modified.

## Prepared

- Pinned official source and inspected CLI, authentication, bootstrap,
  GitHub selection and Docker execution behavior.
- Recorded the five comparison inputs and their revisions.
- Verified official date-window selection covers those inputs and 11 other
  same-day PRs, before native filters. No selector bypass is proposed.
- Selected the user-authorized existing GLM-5.3 service, with no paid fallback,
  at most 20 bootstrap turns per repository and three repository bootstraps.
- Recorded source hashes and a provisional launch plan. This plan is not an
  executable, fully frozen protocol.
- Ran two bounded connectivity probes on existing reserved CPU capacity.
  Their results and authoritative terminal states are recorded separately.

## Blocking prerequisites

1. **Remote GitHub authentication.** The official pipeline invokes `gh`.
   Local authentication works, but no credential has been supplied for the
   remote process. The user has been advised to use a short-lived public-read
   token supplied through an approved secret location. Alternatively, a
   supported browser login can authenticate the actual execution host.
   Do not extract or transfer local credentials. The exact secret location
   or runner login arrangement is still required.
2. **Private GLM connectivity (superseded by OpenRouter selection).** Service discovery succeeds, but the tested TRC-to-
   relay HTTP request produced a `URLError` after approximately ten seconds,
   without an HTTP response. The approved service documentation describes
   callers inside its serving cluster. A supported route reachable from TRC,
   or an explicitly agreed execution-location change, is required. Do not
   bypass the relay, change access controls or start another service silently.
3. **Docker resource containment.** Upstream creates sibling containers on
   the Docker daemon without CPU or memory arguments. The outer Iris
   allocation does not bound those siblings. Before launch, establish a
   dedicated bounded Docker execution arrangement or present an exact
   resource-only adaptation for user agreement. None has been applied.

The user subsequently selected GLM-5.3 through OpenRouter. Private GLM
connectivity is no longer a launch prerequisite; remote GitHub authentication
and Docker resource containment remain unresolved. See `openrouter-preflight.json`.

## Remaining completion requirements

Once access and execution containment are resolved, freeze the actual
configuration, dependency/toolchain pins, supported service route, resource
limits, invocation and artifact retention. Checkpoint executable inputs.
Run the official pipeline with its native outcomes and retry behavior,
without external model repairs. Preserve every attempt and cost record.
Verify any exported tasks through the official grading route with base and
reference controls, keeping native acceptance and diagnostic findings
separate. Publish immutable evidence and a conclusion before closing #25.

The current evidence does not justify a pipeline feasibility conclusion.
