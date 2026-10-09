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
Python parses; ten route-helper tests pass. The upstream package has not yet been
installed and these tests do not establish full Harbor integration, endpoint
reachability, scientific validity or offline enforcement.

Additional execution-boundary work is under discussion: keep the model client
on its supported compute network and use Harbor's native Daytona environment for
task tools. The endpoint patch by itself does not implement that arrangement.
