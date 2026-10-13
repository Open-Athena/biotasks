# Design review 004

One design-only GLM-5.3 call with prompt 3919504; unchanged newer notebook and low reasoning effort. The original response and extracted draft are preserved. JSON schema passes; design review fails. No construction, validation, solver, or viewer update.

Findings:
- Scientific methods remain dependent on unspecified package defaults, and the stated PCA representation is unclear.
- QC checks use submitted post-filter counts for quantities originally computed before filtering; the proposed normalization test also trusts an unvalidated submitted count layer and target.
- Doublet counts alone cannot establish correct per-cell predictions. HVG overlap and marker allowances are arbitrary numerical acceptance values. One required clustering resolution and some scientific artifacts lack substantive verification.
- Source provenance conflates the notebook's initial two-iteration clustering with later clustering calls; resource and cluster-count estimates are described too confidently.

These repeat general contract and verification failures despite explicit prompt instructions. Next comparison holds the prompt and seed fixed and increases reasoning effort, rather than adding notebook-specific rules. This is a configuration experiment, not evidence of a prompt-only improvement.
