# Published comparison artifacts

Two purposively selected examples: SETA breast-cancer cytopathology classification
and BixBench v1.5 `bix-1-q1` (ASXL1 RNA-seq / DESeq2 / GO enrichment).
These are reference examples outside the 12-source candidate list, not generated
BioTasks tasks and not transfer examples. No source or solution was executed.

`cases.json` records links, exact release revisions, inspection findings, proposed
recipes and missing evidence. `manifest.json` records retrieval and SHA-256 hashes.
The BixBench question and notebook retain evaluation provenance and canary text.
Do not stage these comparison artifacts into training or solver inputs.

Both Hugging Face releases declare Apache-2.0 in their dataset cards. The bundled
SETA instruction/test text is attributed to CAMEL-AI's SETA-Env release; the
BixBench question/notebook is attributed to FutureHouse's BixBench release.
See `LICENSE` for the Apache-2.0 license. No upstream text is edited. The explorer
adds clearly labeled inspection notes and proposals; notebook rendering is a
separate derived display.

The BixBench notebook was extracted from a 65,536-byte tail range of its pinned
capsule ZIP. The central directory and selected member CRC were checked by
Python zipfile. No biological input file was extracted. The original 17-cell
notebook includes its saved outputs; these are historical evidence only.

The SETA source identifier resolves to Gabriel Preda's Kaggle R Markdown source,
currently version 96. Its exact generation-time version is not supplied by the
inspected release. Its source hash was recorded. The explorer displays Kaggle’s hosted embed,
with an external source link as fallback; no source redistribution is needed
for that view. The exact generation-time version remains unresolved.
