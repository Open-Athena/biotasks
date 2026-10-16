# Scientific task continuation

The user approved proceeding through a validated task, a blind GLM-5.3 solver
attempt and public release under the existing $100 aggregate spending ceiling.
The fixed-group scope is experiment policy, not a seed-specific factory rule.

## Boundaries

1. **Specification:** GLM reads the existing notebook, reference evidence and
   approved scope. It writes the actual scientific question and explicit input,
   output and comparison proposals. Read-only package inspection is available.
2. **Materialization:** a tool-enabled GLM worker writes a derivation program and
   a solution program. The derivation selects supplied intermediate inputs and
   reference answer fields from immutable evidence. The solution runs separately
   with only task inputs accessible. No handwritten scientific task patches.
3. **Comparison validation:** construct scientific-content comparisons, test the
   new oracle against projected original answers, and challenge them with a
   separate worker's valid alternatives and meaningful errors. Execution and
   repeatability alone cannot establish fair acceptance or software portability.
4. **Harbor and solver:** package only after the comparisons and public question
   agree, execute native controls and a blind solver, then use the upstream release
   workflow and independently verify the published download. Solver success is
   informative, not a requirement to make the task easier.

The specification and materialization workers do not assign a benchmark reward.
Model reviews guide iteration; executable grading determines reward. The viewer
is outside this continuation. Earlier artifacts remain unchanged.

## Materialization execution

Reuse the tested reference sandbox lifecycle and pinned uv environment. Original
inputs are staged by the previously generated, hash-checked setup recipe; original
terminal outputs are restored from the verified replay archive. All generated
code executes in Daytona, not on the shared development VM. Internet is available
for environment/input setup, then blocked before worker tools or scientific code.

The worker submits a complete `Materialization` with the question, declared input
and output paths, a derivation program, a solution program and private rationale.
Controller validation runs the derivation, rejects unexpected paths or symbolic
links, preserves original input/output hashes, and runs the solution as a separate
user with private references and author files inaccessible. It retains the exact
programs, all input/output identities, execution logs and verified downloads.

Successful materialization is explicitly `requires_scientific_validation`: the
controller does not invent a comparison rule or accept numerical disagreement.
The worker may correct rejected candidates within the session's time boundary;
all attempts remain evidence. No numerical tolerances are chosen by this document.

Each session uses the existing two-hour boundary with five minutes reserved for
cleanup, one 4-CPU/8-GiB/10-GiB CPU-only sandbox, a 30-minute setup allowance and
at most ten minutes per derivation or solution execution. GLM uses medium reasoning,
no client token/byte/request-count cap, and a ten-minute individual API timeout.
Only one sandbox is active at a time. The materialization session reserves $2 from
remaining approved funds; this is a conservative hold, not measured billing.

## Independent comparison evidence

For a materialized task, grading first asks a fresh GLM session to implement the
public scientific question from supplied inputs. Its context excludes original
solution code, answer tables and private source review. During that session,
filesystem checks confirm that original answers, the first oracle's outputs and
private author/controller directories are inaccessible. It receives execution
feedback only, not expected scientific values. This is a calibration implementation,
not the later held-out solver attempt, and does not prove universal portability.

The grader then receives original projected answers, the first oracle's outputs
and this independent implementation's outputs. All must satisfy the final
comparator, alongside independently authored wrong-result/valid-representation
probes. A scientific disagreement must be diagnosed, not automatically covered
by a tolerance. The public acceptance addendum is combined programmatically with
the retained question. No grader can remove the scientific question by returning
only a short acceptance document.
