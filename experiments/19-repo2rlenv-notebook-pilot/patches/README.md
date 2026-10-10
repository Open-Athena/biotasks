# Upstream integration patch

Target Repo2RLEnv commit: `55554430cd724efded1f5ad0ff98ebca5d88c0a6`.
Upstream: <https://github.com/huggingface/Repo2RLEnv>.

`0001-custom-terminus-endpoint.patch` exposes the existing Harbor Terminus `api_base`
and `model_info` options to Repo2RLEnv. Custom endpoints require an explicit key
source and cannot contain credentials in their URL. The key travels in the model
client process environment, not command arguments. Route identity enters the
resume check. Responses-agent custom routing remains unsupported; model fallback
remains prohibited. Existing task network policy is unchanged.

Apply to a clean checkout of the exact upstream commit with `git apply --check`
then `git apply`. Do not apply to the BioTasks checkout or silently upgrade the
upstream pin. No fork has been made. Private endpoint values are runtime inputs
and must not enter public evidence; upstream command/config receipts still need
publication review.

Validation so far: patch applies to the inspected pinned source files; all patched
Python parses; ten route-helper tests pass. The upstream package has subsequently been installed from its lock, and affected
regressions plus mocked integration tests pass. These do not establish endpoint
reachability, scientific validity or live offline enforcement.

The agreed execution-boundary adaptation keeps the model client
on its supported compute network and use Harbor's native Daytona environment for
task tools. The endpoint patch by itself does not implement that arrangement.

`0002-external-execution-adapter.patch` adds a caller-supplied execution adapter to
SETA's existing runner. The default worker/Docker path remains intact. It also
lets the upstream trial runner invoke Harbor's native Daytona backend, rejects
network expansion in any execution phase, and accepts an agent-only time bound.
Explicit CPU, RAM and storage overrides apply to Harbor's Daytona execution;
GPU requests are rejected. The adapter caps the whole-trial timeout at 1,500 seconds.
The experiment's `iris_execution.py` supplies that adapter and reuses the original
quality-loop evidence importer. Apply patch 0002 after patch 0001.

The same patch adapts the remote job supervisor's cleanup: Daytona jobs receive
a unique ownership label and select only that label for deletion and subsequent
verification. Docker jobs retain their original cleanup. Nonzero or interrupted
Daytona jobs remain unresolved even if the immediate listing is empty, since a
provider-side creation could still be pending. The adapter refuses subsequent
trial dispatches until the previous claim has verified cleanup.

The pinned dependency and Harbor/Daytona extras have now been installed from the
upstream lock in an isolated local checkout. Affected upstream regression tests
and mocked control-plane integration tests pass; live execution remains pending.

`0003-notebook-design-guidance.patch` adds optional system guidance to the existing
SETA design call. The default call and response schema are preserved. The caller
supplies the version-controlled notebook-grounding prompt to both design and
construction, keeping the adaptation reusable across notebook sources. Apply this
patch after 0002. A mocked call test verifies the unchanged schema, request
settings and seed payload. All three patches were applied sequentially to source
from the pinned archive and compared byte-for-byte with the inspected checkout.

`0004-json-safe-usage.patch` fixes the observed campaign-001 failure: LiteLLM's
nested token-detail objects survive a shallow `dict(usage)` conversion and then
break JSON evidence writing. Use the response model's JSON-mode dump to preserve
those fields as plain data. The regression test uses the installed LiteLLM Usage
class, including nested reasoning-token details, and verifies their preservation.

`0005-idempotent-owned-cleanup.patch` handles a deletion race observed in
campaign 008: Harbor exits successfully, but deleting a resource from the
supervisor's earlier listing reports NotFound. Record that response, then
independently read the exact ID and re-list the ownership label. A delete 404
alone is never sufficient evidence of successful cleanup. Other errors still
fail closed; ownership guards and interrupted-creation handling are unchanged.

Campaign 009 also exposed a stale final listing: a deleted ID reappeared in the
list after direct read-back returned NotFound. Patch 0005 now independently
reads every final listed ID, recording absent/destroyed entries separately.
A live ID, wrong ownership or non-NotFound provider error still fails cleanup.
