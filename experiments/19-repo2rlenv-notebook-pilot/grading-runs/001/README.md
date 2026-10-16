# Grader 001: basic controls pass; independent validation unfinished

GLM produced a candidate with 16 named checks. The controller accepted the saved
reference outputs and rejected the empty submission and each of the three
missing-file submissions. All five controls completed with valid reports.
**This candidate is not ready for Harbor packaging:** the independent probe
worker exhausted the remaining working time before submitting its suite, so no
independent scientific probes, final review or repair ran.

Inspect the unmodified [acceptance contract](acceptance-contract.md),
[grader code](grade.py), [check inventory](check-inventory.json), and
[author's private rationale](author-rationale.md). The contract accompanies the
existing [analysis brief](../../specification-runs/013/task-brief.md); it is not a
standalone replacement for those analysis instructions. The rationale contains
private observations and self-reported development tests and is not solver input.

## Executed evidence

| Controller case | Grader result | Control outcome |
| --- | --- | --- |
| Saved reference outputs | All 16 checks pass | Pass |
| Empty submission | Reject, valid report | Pass |
| Missing per-cell artifact | Reject, valid report | Pass |
| Missing marker-gene artifact | Reject, valid report | Pass |
| Missing parameter artifact | Reject, valid report | Pass |

[Complete basic-control reports](basic-controls.json) preserve each candidate hash,
expected outcome, output identities and per-check report. These five cases do not
establish scientific discrimination or representation handling. The author's
reported 78 mutation families are development claims/evidence from that same
session, not a separately authored validation suite.

| Session | GLM requests | Elapsed | Outcome |
| --- | ---: | ---: | --- |
| Grader author | 112 | 75.64 min | Candidate submitted; five basic controls pass |
| Independent probe author | 23 | 36.72 min | No submitted suite; insufficient time for its next tool operation |
| Final review / separate repair | 0 | — | Not reached |

All 135 requests are recorded as `response_received` in the [request ledger](requests.sqlite).
The original [author operation](grader/artifact-stage/operation.json),
[probe operation](probes/artifact-stage/operation.json) and [campaign result](result.json)
record the stage boundaries and incomplete status. This was a working-time limit,
not a failed reference computation or a demonstrated failure of a scientific probe.
The first export attempt also ran out of its remaining allowance; the bootstrap's
final export completed and independently download-verified the archive afterward.

The campaign used GLM-5.3 medium, one CPU-only 4-CPU/8-GiB/10-GiB Daytona sandbox,
and the [recorded limits](configuration.json). No full notebook rerun, solver,
Harbor packaging, release or viewer update occurred. The $2 reservation is a
conservative allowance under the existing $100 authorization, not a measured bill.
No automatic replacement campaign was started.

## Operator review and next revision

The candidate uses parsed content and dynamically reads expected values. It
compares float32-backed outputs after binary32 rounding, p-values as parsed
doubles, literal cluster identities, and ranked genes with a narrowly defined
tie permutation rule. Those are proposed acceptance rules; their independent
boundary and wrong-result controls remain unexecuted.

The generated text also needs attention before packaging:

- The CSV format sentence says “no quoting of values that contain commas,” which
  conflicts with normal CSV escaping and is confusing beside the parser's support
  for quoted fields. State the intended serialization rules accurately.
- It requires “exactly” three files while saying other files do not influence
  grading; the author reports accepting extra files. Make that policy unambiguous.
- It refers to a check table that is not present in the returned text. The separate
  structured check inventory exists; packaging must explicitly assemble the public
  documents rather than leave dangling references.
- State binary32 acceptance using the actual rounding operation. A loose
  “half-ULP from the reference” paraphrase is not a substitute for the exact rule,
  especially at representational boundaries. Independent boundary probes are pending.

No generated task text or code was manually corrected. The main workflow finding
is that the author spent most of the window performing its own broad inspection
and mutation campaign, then the independent worker repeated considerable
inspection. Another run should narrow these responsibilities and reuse the
accepted candidate rather than repeat authoring from scratch. No new numeric
request/token cap or seed-specific factory rule was introduced.

## Inputs and preservation

Factory checkpoint: `015532adba77b147b0879a19a6bd13696f9dec23`.

- [Author input](grader/input.json) and [actual prompt](grader/system-prompt.md).
- [Independent probe input](probes/input.json) and [actual prompt](probes/system-prompt.md).
  The probe context includes the public instructions and check requirements, not
  the grader implementation. This input was reconstructed from verified source
  fields and matched its original archived byte count and SHA-256 exactly.
- [Environment/isolation evidence](grading/isolation.json), pinned package list
  and uv lock are retained alongside the run.
- [Artifact manifest](artifact-manifest.json) records the 27 retained original
  small files, derived display files, and every archived file identity. The complete
  archive contains 709 files, 222,623,420 bytes; remote upload/download hashes
  matched. Bounded local recovery returned 540 original diagnostic files. Large
  model/tool traces remain in the existing campaign archive, not in Git.
- [Independent cleanup observation](cleanup-observation.json) found zero remaining
  owned sandboxes. The Iris host is terminal. Its failed status reflects the
  incomplete stage, not missing final archival evidence.

Fifty-five focused offline tests passed before launch. A subsequent generic
controller fix ensures an outer SIGTERM reaps the generated process group; all
12 focused grader tests passed, including a real synthetic termination test.
That fix was made after the launch and does not change this run's frozen code
or supply missing scientific validation.
