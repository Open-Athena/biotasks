# Reference preparation, run 002

[Read the worker plan](plan.md), or inspect the original [structured output](plan.json).
The [setup script](setup.sh), [proposed reference script](reference.py) and
[source diff](source.diff) are generated proposals. None has been executed.

**Not ready for execution.** Static inspection found that setup only makes an
empty `/work/venv` directory, then invokes its nonexistent Python executable.
It also contains a placeholder import and a syntactically invalid Python check,
and uses Bash despite the POSIX-shell contract. The model's `prepare` decision
and all output files are preserved unchanged. [Inspection findings](inspection.json).

GLM-5.3 at requested medium reasoning used one creation call and one repair.
The first submission omitted required fields and encoded `changes` as a string;
the repair passed the schema, branch/artifact mapping, source-anchor and Python
reference-syntax checks. These checks do not validate setup behavior or scientific
fidelity. The plan proposes six artifacts across seven branch records, with three
source edits and no capture edits. The custom dotplot aggregation helper from the
preceding proposal is absent. Full-state export justification and unsupported
environment claims remain concerns.

The exact [model input](prepare/input.json), [system prompt](prepare/system-prompt.md),
both requests/responses and the controller trace are preserved. No prior plan or
notebook-specific feedback was supplied. No data staging, sandbox creation,
setup, analysis, independent model review, construction or solver attempt ran.

The request omitted `max_tokens` and extra input/response byte caps. Provider
limits still apply; the existing 600-second timeout per request remained in
place. [Execution receipt](run-receipt.json); [stage result](result.json).
