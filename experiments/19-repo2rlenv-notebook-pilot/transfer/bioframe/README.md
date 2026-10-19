# Bioframe transfer candidate

Selected with the user as the second notebook before pipeline promotion. Keep
factory prompts frozen at the revision in `intake.json`; record any general
infrastructure changes separately. Task-specific exports, instructions and
repairs remain worker-owned.

The pinned notebook is bioframe's motifs-to-CTCF-peaks tutorial. Its 14 code
cells parse as ordinary Python. This is only a syntax check: the deterministic
converter has not run because the shared heavy-work lock was held. No model,
setup, reference, task construction or solver run has occurred.

ENCODE metadata reports both referenced files released for GRCh38, with
compressed sizes 649,474 and 8,211 bytes. No biological input was downloaded.
`data-access.json` records accessions and provider checksums; `motif-access.json`
records the exact JASPAR URL check. JASPAR redistribution terms remain to be
verified independently of bioframe's MIT license.

Next: finish data availability/provenance checks, run unchanged conversion and
preparation, then assess setup and reference execution. Preserve actual failures;
do not predesign the resulting task or silently change notebook semantics.
