# Artifact-grader construction and controls

This stage turns specification 013 into a candidate executable grader using the
saved terminal outputs from setup 001 and the two successful reference repeats.
It does not rerun the notebook. It precedes Harbor packaging and a blind solver
attempt; passing here is not a released task or software-portability evidence.

## Inputs and worker sessions

The controller restores the archived outputs with byte counts and SHA-256 checks,
rebuilds the recorded uv environment, verifies the lock and installed package list,
and blocks sandbox network access. The original script, append-only exports,
setup diff, specification, output audit and repeatability results are explicit
worker inputs. The reference recipe and selected exports remain fixed.

1. **Grader author:** GLM-5.3 writes public instructions, a Python artifact grader,
   named checks and a private rationale. It can inspect the reference outputs and
   installed packages through a shell. Each submitted candidate runs against the
   reference, an empty submission and a submission missing each required file.
   Failed executable checks return feedback through the existing Tasksmith
   submit/revise mechanism.
2. **Probe author:** a separate GLM session sees the same scientific evidence,
   public instructions and named requirements, but not the grader implementation.
   It proposes deterministic wrong-result controls covering each scientific check
   and justified valid-representation controls. Scripts run on fresh copies of
   the outputs; a nonzero exit, missing required file or unchanged submission is
   an incomplete probe, not a successful rejection.
3. **Review:** another GLM session inspects the candidate, probe rationale and
   executed results. It checks scientific coverage, tolerances, public/private
   consistency and what the controls actually establish. It cannot accept a
   candidate with failed controls or unresolved issues.
4. **Optional repair:** at most one separate author repair session, followed by
   fresh execution of all frozen controls and a fresh review. The check inventory
   and probes remain frozen. A necessary scope change is reported as a blocker.

These are fixed sessions with tool-use turns, not fixed raw API-call counts.
Only GLM creates task-specific code and repairs. Generic controller code validates
schemas, runs commands and evaluates the Boolean control expectations.

## Execution contract

The grader receives `--reference-dir`, `--submission-dir` and `--report`. It emits
all declared check IDs exactly once with Boolean results and an overall AND.
An invalid submission must produce a failed report; a crash, timeout or malformed
report cannot count as rejection evidence. Grading compares parsed artifacts,
not reference file hashes. Numerical acceptance rules need explicit justification
and executed boundary controls; byte-identical repeats alone do not validate
arbitrary tolerances or equivalence across implementations.

Authoring, probe execution and grading run under separate unprivileged numeric
users. Reference copies are read-only, controller files and logs are private, and
probe authoring starts after deleting the previous test case. A filesystem probe
checks those permissions before model work. Generated subprocess groups are
terminated on completion or timeout. This is a development isolation boundary,
not a claim of hardened adversarial sandboxing.

## Bounds, records and stopping

Use the existing CPU-only 4-CPU, 8-GiB, 10-GiB Daytona environment and one reserved
2-CPU/4-GiB Iris host. The campaign is bounded by two hours, with the final five
minutes reserved for cleanup; setup allows 30 minutes. Each grader or probe
execution allows 120 seconds. GLM uses medium reasoning and the approved endpoint,
with a 600-second request timeout and no added token, byte or request-count cap.
There is no solver attempt or automatic replacement campaign.

Reserve $2 under the already authorized $100 aggregate ceiling. The resulting
$100 of conservative reservations is not measured provider expenditure. Reconcile
unused reservations before any further campaign.

Preserve rendered inputs/prompts, raw model responses, every candidate, probe
scripts, control reports, input/output hashes, environment checks and cleanup
results. Large reference files remain in the verified archive. Probe mutations
are reproducible scripts plus hashes, rather than retained copies of every
mutated matrix. Review acceptance means **candidate ready for Harbor packaging**;
packaging isolation, a blind attempt and release checks remain later stages.
