# Design-only iteration criteria

Scope: improve the reusable design prompt, using the current notebook as a development seed. GLM chooses the task; preserve every generated response. No construction or viewer changes. These reviews assess design quality, not native execution or scientific validation.

## Review criteria

1. **Defined method:** one coherent scientific objective and explicit consequential choices; software alternatives must implement that method.
2. **Source fidelity:** source-derived choices can be traced to the notebook, and proposed changes or omissions are explicit and justified.
3. **Public contract:** outputs and acceptance requirements are unambiguous and consistent throughout; no hidden scientific requirements or reference answers.
4. **Verification coverage:** required results are checked against trusted data or independent derivations, not only shape, recognizable names, or consistency among submissions. Checks respect the stage, representation, and valid symmetries of the result.
5. **Honest uncertainty:** no invented measurements or acceptance thresholds; remaining runtime, numerical calibration, and reproducibility questions are explicit construction gates, not permission to weaken correctness.
6. **Response contract:** exactly the requested JSON fields and valid types/lengths, with readable final prose.

## Iteration discipline

Change only general instructions that address a failure mechanism. Do not add seed-specific methods, parameters, genes, expected answers, or grader rules. Keep the input seed unchanged and preserve failed drafts. Do not manually correct the worker's output.

Once a draft satisfies these design-level criteria, repeat the same prompt without changes to assess consistency. A repeat on the same seed is not a generalization test. Evaluation on held-out notebooks from other domains remains necessary before claiming broader reliability.

If repeated prompt revisions do not resolve the same failure mechanism, report that limitation rather than adding a growing list of notebook-specific exceptions. Construction-time evidence remains necessary even for a satisfactory design.
