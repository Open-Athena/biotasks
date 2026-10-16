# Initial independent authoring review

All three candidates passed the pinned author's schema checks. This does not
establish usable instructions or task acceptance.

- `3708e0e3d5e89cd5ba4a` (simpson_d): reject the instruction. It contains 555
  repetitions of the heading and no substantive implementation requirements.
  The original response has finish_reason=stop and the resulting markdown is
  19,999 characters, just below the schema maximum. Preserve it unchanged.
- `d86a2e7a9853ecd4b5eb` (simpson): semantic review pending. The generated
  finite-sample bound and unconditional no-exception claims need checking
  against the reference and its called functions. Literal `n` characters occur
  where Markdown newlines were intended.
- `c80f6a9306c83c7db638` (observed_features): the requested alias relationship
  agrees with the saved reference body (`return sobs(counts)`). Full semantic,
  control and grader/isolation checks remain pending. Its Markdown also has
  literal `n` characters in place of newlines.

Raw specification responses contain these same formatting defects; recovery did
not introduce them. No automatic replacement of literal `n` is justified. No
solver attempts or independently accepted tasks are claimed.
