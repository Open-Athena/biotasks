# Sonnet model comparison prepared

The user requested a second run with the pinned upstream docs' example model,
Claude Sonnet 4.6, using the same inputs and budgets as the GLM baseline.

All five JSON configurations differ from the original arm only at `llm.model`:
`z-ai/glm-5.3` becomes `anthropic/claude-sonnet-4.6`. OpenRouter remains the provider.
The runner, source revision, native prompts/parser, output-token budget,
temperature, turn/time/spend limits, selection windows, repository refs and Docker
resource guard are unchanged. Shared launcher files are copied byte-for-byte to a
separate temporary staging directory; their hashes are checkpointed in the launch
plan. The fresh controller has an empty bootstrap cache, so GLM's image/cache is
not reused. Run identity and artifact destination differ for isolation.

This is the same research question as #25. Preserve the original negative result
and its evidence at `c20ba1a095949e330c81921d24ce820792f152d2`; report the new arm
separately before comparing them. No external repair or extra model probe is part
of this run. Public endpoint metadata was checked without generation.

Native model calls remain gated until the new controller's GitHub login succeeds
and the original checkpointed native command is explicitly enabled. Any exports
require the same official base/reference control requirement before claiming a
verified task. Record missing diagnostics and cost data rather than filling gaps.
