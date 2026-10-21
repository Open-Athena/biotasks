# Fresh PyHMMER autonomous campaign 023 — grading transport failure

Factory `47ebdb2b8fb51993c06c679e79845fb6541cc28b` completed preparation, setup/offline reference execution, two reference repeats, specification and task construction without operator intervention. Its independent implementation also executed and produced both declared outputs; those outputs were not yet scientifically compared.

The first grader-model request then timed out after its existing 600-second allowance. The retained receipt identifies `TimeoutError` / `transport_uncertain`; it does not establish why the provider did not respond. No response or grader was accepted for that request, and uncertain transport is not automatically replayed. The pipeline recorded `infrastructure_failed` at grading. This is neither a validated task nor a scientific notebook rejection; no native solver ran.

Pipeline duration was about 44 minutes 37 seconds; host lifetime including evidence export was about 49 minutes 32 seconds. Specification took about 18 minutes 37 seconds, construction 3 minutes 44 seconds, and grading 18 minutes 1 second including the failed request. Small original receipts were recovered and hash-checked; complete execution evidence remains in the verified private archive.

All four sandbox-stage cleanup receipts passed. A separate provider inventory at 20:58 UTC found zero owned sandboxes. The host is terminal. The original unstarted 019–022 outcomes remain unchanged; no generated candidate was hand-edited. Further work is to diagnose/recover the grading transport boundary through reusable factory code and preserve this failure.
