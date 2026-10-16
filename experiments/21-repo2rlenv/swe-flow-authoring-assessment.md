# SWE-flow authoring handoff

Source: Repo2RLEnv 27d04ee8203cd5b2f20c3997d13836e5f5b64238,
`src/repo2rlenv/pipelines/recipes/swe_flow/author.py` and
`src/repo2rlenv/pipelines/repo_reconstruct.py`.

The completed worker stage only traces healthy tests, schedules dependent
functions, removes their implementations, and measures execution contrasts.
It does not author instructions or export a released task.

The native author has two ordered model stages per candidate: function docstrings
and a specification. Each uses structured validation with up to three attempts,
so three candidates can require up to 18 calls. Native output allowance is 6,000
per request. The approved generation adaptation permits 131,072 combined output
tokens with medium effort and a 1,200-second timeout; the two-hour run deadline
still bounds a cohort even if not all correction attempts fit. Partial responses
and failed stages must be retained.

Do not reuse the SWE-smith issue writer for these candidates: it has a different
prompt, schema, and two-attempt repair contract. The existing generation adapter
patches only the SWE-smith module's metering reference. SWE-flow instead imports
`validated_complete`, whose metering reference is in `campaigns.structured`.
Extend the adapter with an explicit scoped metering target and check actual
request/receipt behavior offline before launching authoring.

The native export applies generated docstrings to the skeleton and then runs
Harbor nop and oracle controls, requiring completed rewards 0 and 1 before the
final export. Controls on a bare skeleton are insufficient because generated
docstrings alter the learner-visible task. Independent instruction review,
verifier isolation, and Marin runtime checks remain separate acceptance gates.
