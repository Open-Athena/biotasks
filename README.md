# BioTasks

BioTasks is an open effort to generate realistic computational biology tasks
with reproducible inputs and executable grading. The aim is to turn scientific
workflows into tasks that require agents to use bioinformatics tools to
answer biological questions.

The proposed pipeline discovers source workflows, curates observed biological
data, authors task variants, and independently validates their reference
solutions and graders. Tasks are intended to be packaged for Harbor and usable
by other pipelines.

The project is in early development. The scientific design and initial prompt
templates are under review; there is no runnable generator yet.

Read the [design documentation](docs/README.md) for the proposed pipeline,
task requirements, and a worked example.
