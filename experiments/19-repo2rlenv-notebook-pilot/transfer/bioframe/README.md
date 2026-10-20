# Bioframe transfer candidate

Selected with the user as the second notebook before pipeline promotion. Keep
factory prompts frozen at the revision in `intake.json`; record any general
infrastructure changes separately. Task-specific exports, instructions and
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

[Preparation 001](preparation-runs/001/plan.md),
[setup/reference 001](setup-runs/001/README.md),
[deterministic replay 001](replay-runs/001/README.md), and
[specification 001](specification-runs/001/README.md) are complete.
[Materialization 005](materialization-runs/005/README.md) produced an executed
candidate whose oracle matches the projected reference. Fresh scientific
validation 002 is in progress: its independent implementation and five initial
controls passed; verifier probes and review remain pending. Native Harbor
controls, a blind solver attempt and publication have not run for this case.
Original worker outputs remain unchanged; no task-specific scientific repairs
were made by the operator.

The setup trace exposed a factory limitation: the worker ran additional full
analyses through its shell despite the prompt, outside the controller's test
count. See the setup record for the exact evidence and limits. The original
notebook and all canonical prompts remain unchanged.
