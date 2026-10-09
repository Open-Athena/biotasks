# First execution budget — agreed 2026-10-09

The user approved these bounds on 2026-10-09. This is not a launch receipt. The integration has local control-plane
tests, but no live compatibility or scientific validation. Complete and test
request accounting and the launcher before dispatch.

Use one Iris host on existing reserved CPU capacity: 2 vCPUs, 4 GiB RAM, 20 GiB
storage, no accelerators, one job, no automatic restarts. Limit the campaign to
two hours, then allow five minutes for evidence export and cleanup only. No new
paid Iris capacity or inference deployment is permitted by this proposal.

Use one active Daytona task sandbox at a time: 1 vCPU, 2 GiB RAM, 10 GiB disk, no
GPU. This matches upstream's CPU/memory task defaults. The PBMC matrix is sparse;
QC/normalization does not require full clustering or a dense full-matrix copy.
These are proposed ceilings, not measured scientific resource requirements.

- Environment build: 600 seconds per trial. Provider-side build resource allocation
  still needs checking; task resource limits do not prove build-worker limits.
- Reference/oracle: at most 600 seconds; verifier: 120 seconds.
- Blind solver: 300 seconds of model/tool execution, at most 12 harness turns,
  and at most 24 outgoing inference requests per attempt, including retries.
- Whole trial including setup: at most 1,500 seconds, also bounded by the enclosing
  campaign deadline. An observation timeout requires reconciliation, not relaunch.

Model request allocation (all GLM-5.3, no fallback):

| Phase | Maximum outgoing requests |
| --- | ---: |
| Small compatibility checks | 4 |
| SETA design + initial construction + two construction repairs | 4 |
| Shared quality review, probes, one repair and re-review | 24 |
| First solver attempt | 24 |
| Second solver attempt after repair | 24 |
| Total | 80 |

These are maxima, not target usage. The quality request allowance does not add
repair rounds or new solver attempts. Calls with uncertain outcomes count. A
request gate must enforce these limits across processes before running; upstream
USD estimates and turn limits alone are insufficient. Use at most 16,000 output
tokens for construction, 8,000 for quality, and 8,192 per solver response, with a
120,000-token harness input budget (tokenizer estimates must be disclosed). Compatibility probes use at most 512 output
tokens. No context should be silently truncated to make a candidate fit.

At most 16 task trials: up to six generation controls (no-op/oracle for three
builds), then up to ten quality trials (no-op/oracle/two probes/solver for each of
two revisions). The existing two-solver cap still applies. A bounded infrastructure
preflight is separate from scientific trials and may use one extra sandbox for at
most ten minutes to check connectivity and offline enforcement. No scientific task
is manually created for that preflight.

Agreed external compute/storage ceiling: USD 1 for Daytona, excluding already
reserved Iris capacity and the approved free inference service. Reconcile actual
usage and retained snapshot storage; stop creating resources if the conservative
remaining-cost reservation exceeds this ceiling. The sequential task resources
above cost about USD 0.167 for two continuous sandbox-hours at the published
rates, before build/storage differences; this is an estimate, not a provider
billing cap. Rates inspected 2026-10-09 at https://www.daytona.io/pricing:
USD 0.0504/vCPU-hour, USD 0.0162/GiB-hour RAM, and USD 0.000108/GiB-hour disk after
five free GiB. If build accounting cannot be bounded, ask before proceeding.

Before task generation, require successful endpoint/schema compatibility, an
actual offline-tool/verifier check, and verified data staging. Preserve failures;
do not spend generation slots on infrastructure failures or retry automatically.
Publish only after the issue's scientific, probe, blind-attempt and integrity
requirements pass. Exhaustion leaves an unmet outcome, never implied success.
