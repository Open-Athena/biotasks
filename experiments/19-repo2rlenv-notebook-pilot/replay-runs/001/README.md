# Reference replay 001: all terminal outputs reproduced exactly

Two fresh offline executions reproduced **all three terminal artifact files
byte-for-byte**, both against the original setup reference and against each
other. This is positive repeatability evidence for the pinned workflow. It is
not a validated grading contract or a claim of equivalence across other stacks.

| Observation | Replay 1 | Replay 2 |
| --- | ---: | ---: |
| Complete reference runtime | 223.60 s | 178.18 s |
| Maximum child-process RSS | 4.94 GiB | 4.77 GiB |
| Required artifacts reproduced | 3 / 3 | 3 / 3 |
| Exact artifact hashes match original | Yes | Yes |
| Reference exit status | 0 | 0 |

Both runs fit the 600-second reference limit and used the agreed 4 CPUs,
8 GiB RAM and 10 GiB disk, with no GPU. Maximum child RSS is not aggregate
sandbox memory. The original reference took 147.5 seconds; that single timing
was not a guarantee of subsequent runtime.

## Inputs, program and outputs

- [Actual configuration](configuration.json) and
  [controller input hashes](replay/frozen-inputs.json).
- [Frozen setup snapshot](../../setup-runs/001/README.md), including the generated
  analysis, append-only exports, input receipts and dependency lock.
- [Programmatic replay implementation](../../reference_replay.py) and
  [execution contract](../../reference-replay.md). **There is no LLM prompt or
  model call in this step.** The original request ledger records zero calls.
- [Replay 1 record](replay/trials/1/result.json),
  [replay 2 record](replay/trials/2/result.json),
  [comparison summary](replay/comparison.json), and [final status](result.json).
- [Evidence manifest](artifact-manifest.json): original small-file hashes and all
  six generated output-file hashes; complete outputs remain in the artifact store.

Factory checkpoint: `07aea429cced57cd2a28f341fd34646da2d6967a`.
The controller verified the earlier snapshot and installed its project with the
saved uv lock, without resolving dependencies again. The lock and installed
package list matched the original records. Original input SHA-256 checks passed
before and after each run. Network access was blocked during both computations.
The reference script and exports were unchanged; no scientific or setup repairs
were made.

The sandbox started fresh; each reference used a new process and empty working
and output directories. The two runs shared the rebuilt environment and caches.
The versioned base-image tag was reused; the earlier snapshot did not record an
immutable image digest. These finite repetitions do not establish universal
repeatability across hardware, package versions or implementations.

## What this establishes for grading

The same named/versioned reference workflow can reproduce the chosen target
artifacts exactly in these runs. We can now give a grading worker that measured
fact, together with the reference outputs and specification handoff. It should
not use file-byte equality as the grading rule merely because these hashes match.
Public comparison rules, representation handling, numerical tolerances and
meaningful wrong-output controls still need executable validation.

Forty-four focused offline controller tests and targeted lint passed before
launch. All retained records were checked against their archived hashes, and the
archive exporter independently downloaded and hashed the full output files.
The remote job succeeded and controller cleanup passed. A separate provider
readback is recorded in [cleanup observation](cleanup-observation.json).

No task construction, solver attempt, release or viewer update ran in this step.
The $2 reservation is inside the standing $100 authorization; it is a conservative
ceiling, not an observed charge. Aggregate reservations are $98 and actual
provider billing remains unmeasured.
