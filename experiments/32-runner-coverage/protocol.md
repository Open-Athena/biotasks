# Runner-coverage investigation

Main/upstream and copied source hashes are in `provenance.json`. This first stage has no model calls or remote jobs. The SGR-only parser candidate preserves uncolored status parsing and is checked against explicit expected test-ID/status maps. It intentionally does not claim truncated/timed-out output is complete: a separate execution-completion gate remains necessary. Original task results are never regraded by these fixtures.

`check_parser.py` also loads the exact pure upstream targeting functions by AST to demonstrate broad-path preservation versus pathless targeting without installing dependencies. No command-targeting change is applied yet. The local synthetic check is <100 MiB estimated working set /30 seconds, one worker under the shared nonblocking heavy lock with thread caps and resource evidence.

`sample.json` predeclares six SAMtools rejects using a stable hash ordering of all 219 original decisions. Read-only GitHub metadata and diff acquisition will record current source refs, hashes and retrieval failures, not replace inaccessible cases or silently call current patches exact original bytes. Raw diffs remain local under ignored `inputs-private/` until redistribution eligibility is reviewed. Fetches are capped at 2 MiB per response; findings may cite paths and source links without republishing fixture data. Static regression-case evidence is distinct from proving a native fail-to-pass pair.

## Execution-completion gate comparison

The pinned native validator computes transitions without checking the executor's exit code or requiring both complete output markers. `completion-gate.patch` proposes rejecting nonzero stage execution or absent start/end markers before parsing statuses. Ordinary test failures still use the upstream script's final marker/zero stage exit and can form legitimate F2P transitions. This does not by itself verify every individual shell operation succeeded, or that every collected test ran; those remain additional lifecycle/runner concerns.

`check_completion.py` passes seven synthetic executor outcomes through exact original/candidate validation functions with the real pinned pytest parser. Source-fetch success is stubbed and no shell/container/test is run. Expected results are one preserved complete pair and six rejected incomplete/error cases; this is not a rerun or regrading of Scanpy/MNE. Same <100MiB/30second local resource bound applies.
