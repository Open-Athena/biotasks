# Newer-notebook design response

[Read the model's draft specification](draft-spec.md). This is the unmodified
`draft_spec` field returned by one GLM-5.3 call using the newer Scanpy
`clustering.ipynb` seed and the updated design prompt at commit `dd2d948`.
The system prompt matches the canonical file exactly, with no appended guidance.
The seed contains the full notebook source and factual provenance; no manual
analysis scope was supplied.

The worker selected preprocessing, clustering, differential expression and
marker-based NK-cell identification. Its proposed tolerances, resource estimates,
methodology and fallback reductions have not been approved or validated. This
record preserves the proposal rather than adopting those choices as factory policy.

The response finished normally in 38.95 seconds: one call, zero retries,
7,360 input tokens and 3,246 output tokens. JSON/schema checks passed, with seven
capabilities and a 10,787-character specification. Settings: GLM-5.3, low reasoning
effort, 9,000-output-token cap, temperature 1.0 and top_p 1.0.

No construction, repairs, native scientific validation, solver execution or
Daytona sandbox was started. The HTML viewer was not changed. Stop here for user
inspection before advancing to another pipeline stage.

- `request.json`: exact system prompt, full seed and inference settings.
- `response.json`: original completion and measured call timing.
- `model-output.txt`: verbatim returned JSON message.
- `draft-spec.md`: verbatim extracted Markdown field.
- `manifest.json`: source revision and request/prompt hashes.
- `summary.json`: response/schema outcome and stage boundaries.
