# Reference preparation, run 003

[Inspect the rejected worker draft](draft.md). **No valid preparation plan was
produced.** GLM-5.3 used the creation call and the one allowed repair; both were
rejected. Nothing generated was executed, and no later pipeline stage ran.

The initial submission omitted `changes`, `artifacts` and `branches`. The repair
added incomplete inventories but still omitted `changes` and introduced an
unexpected field, `source_evidence赎`, in a branch. The controller stopped after
two received model responses. Both responses ended with `tool_calls`, not a
reported output-length truncation. The required fields were present in the
submitted tool schema. [Exact validation feedback](validation-errors.json).

The last draft also maps branches to three undeclared artifacts and contains an
unreferenced artifact path, `of PC scores`. Those inconsistencies remain in the
original output; we did not repair them. Without source edits there is no
materialized reference script to review or execute.

The dependency declaration and staging script can still be inspected as
unaccepted proposals: [pyproject.toml](pyproject.toml),
[stage-inputs.sh](stage-inputs.sh). These files and `draft.md` are mechanical
extractions/renderings of the [controller's rejected draft](prepare/artifact-stage/draft.json),
not substitute accepted artifacts. The staging input identifiers and provider
checksums match the supplied provenance; download success, dependency resolution
and scientific fidelity remain unverified.

The run used [checkpoint 8ed5220](https://github.com/Open-Athena/biotasks/commit/8ed5220519ab864421e263157d32bba4f05f83cc)
after an independent factory review and fixes. Medium reasoning was requested,
with no client output-token/input-byte/response-byte caps and a 600-second
per-request timeout. Preparation took 436 seconds and consumed 20,971 prompt
and 78,322 completion tokens across two requests; the latter includes 72,527
reported reasoning tokens. [Execution receipt](run-receipt.json).

All 15 original preparation evidence files were recovered and hash-verified.
The exact [input](prepare/input.json), [prompt](prepare/system-prompt.md), both
requests/responses and the controller trace are preserved unchanged. The remote
host is terminal. No sandbox, setup, analysis, independent model review,
construction, solver attempt or replacement campaign was launched.
