# Reference preparation, run 001

[Read the worker plan](plan.md), or inspect the original [structured output](plan.json).
The [setup script](setup.sh), [proposed reference script](reference.py) and
[source diff](source.diff) are generated proposals. None has been executed.

GLM-5.3 at medium reasoning returned an accepted structured plan in one call;
no repair was needed. The controller checked the output schema, branch/artifact
mapping, exact source anchors and Python syntax. These checks do not establish
scientific fidelity, dependency availability, runtime or output correctness.
The model proposes 21 artifacts mapped to 17 branch records; these are not a
final task or grading contract.

The exact [model input](prepare/input.json) and [system prompt](prepare/system-prompt.md)
are preserved alongside the request, response and controller trace. There was
no data staging, sandbox creation, setup, scientific execution, independent model
review, task construction or solver attempt.

The request omitted `max_tokens` and additional input/response byte caps.
Provider context/generation limits still apply and were not independently verified.
The existing 600-second request timeout remained in place. The result arrived
within it. [Execution receipt](run-receipt.json); [stage result](result.json).
