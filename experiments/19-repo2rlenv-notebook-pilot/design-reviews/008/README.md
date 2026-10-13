# Design revision 008

GLM revised draft 006 using the original notebook, canonical design prompt and unmodified GLM critique 007. High reasoning effort; output budget increased from 9,000 to 16,000 tokens. JSON schema and required sections now pass; original output preserved.

Review still finds blockers: R1's test compares the final filtered artifact with the complete input cell set; R5 asserts a batch aggregation algorithm absent from the notebook; some QC/output definitions and sampling coverage remain ambiguous. Several earlier issues improved, including the normalization formula, declared numerical calibration gates, and attribution of the Leiden iteration adaptation. These improvements do not establish scientific correctness.

Next revision strengthens systematic per-requirement review, and distinguishes a source-defined method from unsupported internal algorithm details. No task-specific method is added to the prompts. No construction, native validation, solver or viewer update.
