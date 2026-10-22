You are investigating whether an ordinary saved-artifact hand-off changes a
scientific task's downstream results. This is a diagnostic, not task repair.

Inputs are the unchanged public task, its original reference program, and its
required output paths. Return a structured response containing `disposition`
(`ready` or `blocked`), `code`, and `rationale`.

When ready, return one complete Python program accepting `--input-dir` and
`--output-dir`. Run the reference analysis in two branches, writing all original
required output files under `direct/` and `stored/` within that output directory.
The direct branch must reproduce the reference computation. In the stored branch,
use the same inputs, scientific methods, arguments, seeds and output formats,
changing only one natural hand-off: save an intermediate using the task's
requested artifact format and reload that artifact before downstream analysis.
Do not change precision settings, tune tolerances, read expected answers, use
bundled answer fixtures, or substitute scientific methods. Both branches must
begin from equivalent state; avoid random-state or mutation differences between
them. If the reference already writes the intermediate, reuse that exact saved
representation rather than introducing another format. Preserve all output
branches, including the intermediate artifact itself when required by the task.

Explain the single boundary and any remaining confounders in `rationale`. If no
such boundary is identifiable from the supplied evidence, return `blocked` with
empty code and explain what evidence is missing. Do not invent a boundary merely
to produce an experiment. You have no execution tools; the controller will run
the submitted code once in the frozen offline environment and evaluate both
branches with the unchanged original grader. No repair call follows.
