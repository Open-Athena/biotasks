# SETA v1 stage-1 pilot

User requested baseline execution on October 6, 2026. Two sequential comparison
cases, each limited to five minutes, using authenticated Codex CLI 0.160.1,
gpt-6-astra, medium reasoning. No paid infrastructure provisioned. Usage tokens
will be preserved when returned; monetary cost is unavailable for this login.

Use unchanged SETA prompts and extracted preload functions at 5868a1b. Real
source inputs staged locally under ignored downloads/, with hashes and URLs in
input-manifest.json. SETA R Markdown source is not converted into a synthetic
notebook; its filename and format are explicit in metadata. BixBench remains
comparison-only. No previously released task instructions, solutions, ideal
answers or our inspection notes enter the worker input.

Harness deviations: Codex rather than SETA's Claude runner; a stage-1-only tool
policy forbids scientific execution, network and agent launch. Existing package
and model instructions are not claimed identical. The raw prompt and command
are recorded. The unchanged preload silently omits a notebook outline when its
upstream extraction fails; this behavior is preserved. Model context/output-token
caps and dollar caps are not enforced by this CLI; the hard bounds are two jobs,
300 seconds each and shared-node resource limits. No acceptance scores follow
from draft production. Builder execution is a separate subsequent stage.
