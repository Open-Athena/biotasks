# Bioframe transfer candidate

Selected with the user as the second notebook before pipeline promotion. The initial baseline
uses the prompt revision in `intake.json`; subsequent general factory changes
and each run's exact prompts/inputs are recorded separately. Task-specific exports, instructions and
repairs remain worker-owned.

The pinned notebook is bioframe's motifs-to-CTCF-peaks tutorial. Its 14 code
cells parse as ordinary Python. The deterministic converter initially rejected
Jupytext file-pairing metadata. A general converter change now records the
`formats` field without passing it to the exporter. Conversion preserves the
ordered executable AST and Markdown as comments. No notebook-specific source
repair was made. The user authorized proceeding without the shared lock for
this lightweight conversion; load and memory checks remained in place.

ENCODE metadata reports both referenced files released for GRCh38, with
compressed sizes 649,474 and 8,211 bytes. The intake checks preceded biological input downloads; the setup worker subsequently staged the original files.
`data-access.json` records accessions and provider checksums; `motif-access.json`
records the exact JASPAR URL check. JASPAR's official About page states CC BY 4.0; its URL is recorded in
`intake.json`. This permission is independent of bioframe's MIT license.

The [current task is published and fresh-download verified](scientific-releases/001/README.md).
[Final grading 004](grading-runs/004/README.md) passed all 15 scientific controls.
[Native Harbor 001](native-runs/001/README.md) returned oracle 1, no-op 0 and blind
GLM-5.3 solver 1, without exceptions. The solver took about 3 minutes 30 seconds
and seven successful model requests. All owned sandboxes are absent and the host
is terminal. The shared HTML explorer now selects this case.

[Preparation 001](preparation-runs/001/plan.md),
[setup/reference 001](setup-runs/001/README.md),
[replay 001](replay-runs/001/README.md),
[specification 001](specification-runs/001/README.md) and
[executed construction 005](materialization-runs/005/README.md) preserve the
selected inputs to validation. All generated scientific content and repairs came
from versioned GLM workers; no task-specific scientific artifact was manually
patched. General defects required operator recovery, so this is not evidence of
a fresh unattended end-to-end run. See the logbook and run records for failures,
reused prerequisites and timing limits.

The setup trace exposed a factory limitation: the worker ran additional full
analyses through its shell despite the prompt, outside the controller's test
count. See the setup record for the exact evidence and limits. The original
notebook and all canonical prompts remain unchanged.
