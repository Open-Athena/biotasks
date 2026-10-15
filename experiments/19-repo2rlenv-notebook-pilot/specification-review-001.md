# Independent specification-stage review

Reviewed checkpoint: `9eb772559d3691dc541390db4858843fcddfdfd7`.
Reviewer: separate Codex agent `review_specification_stage`, requested by the
user on 2026-10-15. Read-only review; no model-worker request, remote execution
or implementation changes. Findings describe that checkpoint; their disposition
is recorded below.

## Changes recommended before the model call

1. **Restore the agreed validation requirements.** The canonical
   `notebook-task-specification.md` validation section asks generically for
   meaningful wrong-result controls and discusses when alternatives are needed.
   The full proposal requires the reference to pass; empty and missing-endpoint
   submissions to fail; a consequential control for each scientific branch; and
   independently computed conforming alternatives wherever numerical or software
   portability is claimed. Carry those requirements into the prompt. Copying or
   reformatting reference outputs tests representation handling, not independent
   computational validity. See proposal lines 390–408 and prompt lines 91–98 at
   the reviewed revision.

2. **Separate instructed methods from verifiable output properties.** Some
   required computations leave no distinctive signal in selected terminal
   artifacts. Require the private plan to name consequential methodological
   distinctions those artifacts cannot establish. Do not invent intermediate
   exports, claim unverified procedural compliance or silently weaken the
   scientific contract. See proposal lines 383–388 and prompt lines 66–67 and
   91–103 at the reviewed revision.

## Evidence limitations and optional simplification

The text-only worker may correctly return `needs_evidence`. Implicit package
defaults and manual biological annotations keyed to arbitrary cluster numbers
may require further inspection. In this source, the mapping occurs in
`setup-runs/001/inputs/original.py` lines 283–289. Populated annotation labels do
not establish biological validity or portability. The current prompt correctly
warns against inventing these semantics. An evidence request is not a worker
failure.

Optionally replace the full uv lock in model context with a deterministic
package/version summary and the preserved original lock hash. It contributes
about 127 KB of the 226 KB bundle, much of it wheel hashes and URLs unnecessary
for scientific specification. Preserve the actual lock as execution evidence;
do not introduce arbitrary input byte caps. This is not a launch blocker.

No blocker was identified in the four-field response envelope, blocked-response
handling, original-file hash checks or output/audit lineage checks. The reviewer
performed source inspection only, not additional tests or scientific validation.

## Author response — 2026-10-15

Both requested prompt changes are addressed in the canonical
`notebook-task-specification.md` validation section:

- The private plan must include reference, empty/no-op, each missing-endpoint,
  and consequential per-branch wrong-method/result controls. Claims of numerical
  or software portability require an independently computed conforming
  alternative using only the public inputs and contract. Representation-only
  changes to reference outputs cannot substitute for that computation.
- The plan must identify methodological distinctions that selected terminal
  artifacts cannot establish. It must limit verification claims explicitly and
  flag or reject an uncheckable required scientific distinction, without adding
  intermediate exports or silently changing the contract. Unexecuted controls
  and unsupported portability claims remain unvalidated.

These changes are general and prescribe no notebook-specific method, artifact
or threshold. The input bundle and four-field schema are unchanged. The optional
lockfile summarization is deferred: it is not needed to address either finding,
and the current exact evidence remains available for this first specification
pass. A justified `needs_evidence` response remains an acceptable outcome.

The four existing prompt/CLI checks and whitespace validation passed. No new
model request, scientific execution, task construction or viewer update.

## Subsequent evidence-presentation change

After run 001, the optional lockfile summarization was adopted for run 002 and
later inputs. The full lock is still retained and hash-checked; the worker sees
its identity and the exact resolved package/version list. This supersedes the
initial deferral above without changing the original review or run-001 evidence.
