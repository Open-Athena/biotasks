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

Next: run preparation using the unchanged canonical prompt, then assess setup
and reference execution. `preparation-config.json` selects the notebook without
preselecting scientific methods or output schemas. Preserve actual failures;
do not predesign the resulting task or silently change notebook semantics.
