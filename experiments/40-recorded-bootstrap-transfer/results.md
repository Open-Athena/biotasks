# Scanpy transfer assessment

The frozen OHIF wrapper does not transfer unchanged to Scanpy. This is a source-bound retrospective assessment, not a new Scanpy build or failed task-validation attempt. No new remote jobs, model calls or CPU reservation were needed.

| Boundary | Verified evidence | Conclusion |
| --- | --- | --- |
| Native clean export | #38 build exit 100 at apt prerequisites, before controls | Native inline recipe cannot rebuild this frozen package as emitted |
| Recorded environment procedure | Original transcript and cached bootstrap verified; all sixteen actions match #29 replay, including step 7 exit 1 | Recorded execution fidelity is established for that historical attempt, not environment readiness |
| Bootstrap checks | Original and replayed smoke/fresh checks are false; fresh run exits 2 at three collection errors | Replay alone does not remove dependency/configuration failures |
| Outer acceptance policy | Pinned upstream caches and returns flagged images; #39 stops on either failed check | Hard rejection belongs to our wrapper policy; it must not be attributed to upstream pr_runtime |
| Probe interface | Original Scanpy verifier activates `/workspace/.venv`; the OHIF probe requires two PATH exports | A data-only transfer cannot correctly probe this environment as-is |
| Existing task controls | Both original nop/oracle trials time out at 300 and 1200 seconds; all ten task files match the original export | No scored pair or clean command, even in the longer historical arm |

The native-inline failure and historical replay used exactly the same public image ID, `sha256:a33c10a97f11005523814c6eee013986119fe41f3122f444518117536675c8e1`, bound to `python@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704`. All 353 pinned upstream source files, the original phase/transcript/bootstrap, all sixteen action/output records and trial/cleanup archives were reverified. Eight grading assets are unchanged in the native-prepared variant.

The historical fresh checker reports a pandas `future.infer_string` deprecation treated as an error, an unregistered `flaky` pytest marker, and missing `dependency_groups` in a CI helper. None was repaired. The task verifier invokes six original test files, collecting 952 pytest cases while its reward tracks two F2P and ten P2P identifiers; parameterized cases and tracked identifiers are different units. Partial output reaches about 68% at 300 seconds and 90% at 1200 seconds. A failed test is visible near the latter cutoff. These are incomplete logs, not pass rates, final diagnoses or evidence that more time alone would produce valid controls. One raw log contains NUL bytes; its original archive remains intact in the existing public snapshot and its hash/NUL count are recorded rather than rewriting that evidence.

Future work needs separate decisions about faithful flagged-bootstrap handling, language-aware provenance probes, dependency drift and whole-file verifier cost. Those are distinct from changing tests or adding ad hoc install commands. This assessment does not relax any acceptance gate or make the OHIF prototype production-ready. Repeating the unchanged known failures would add little evidence and would conflict with the epic’s stopping rule.

The task remains one original export, with no new unique-task count. Historical attempts are not rebilled to #33. Its allocation stays at 6.127669 CPU-hours, zero CPU reservations/model calls; the existing storage reservation is unchanged. Original public artifacts were freshly downloaded anonymously; new assessment archival and owned-input cleanup are recorded separately.
