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
compressed sizes 649,474 and 8,211 bytes. No biological input was downloaded.
`data-access.json` records accessions and provider checksums; `motif-access.json`
records the exact JASPAR URL check. JASPAR's official About page states CC BY 4.0; its URL is recorded in
`intake.json`. This permission is independent of bioframe's MIT license.

Current progress: [preparation 001](preparation-runs/001/plan.md),
[setup/reference 001](setup-runs/001/README.md), and
[deterministic replay 001](replay-runs/001/README.md) are complete. Specification
001 is submitted with the existing read-only package tools. No constructed,
graded or solved task exists for this notebook yet. Original worker outputs are
preserved; no task-specific scientific repairs were made by the operator.

The setup trace exposed a factory limitation: the worker ran additional full
analyses through its shell despite the prompt, outside the controller's test
count. See the setup record for the exact evidence and limits. The original
notebook and all canonical prompts remain unchanged.
