# Review an artifact grader and its executed controls

Review the generated public instructions, named checks, complete grader code,
independently authored probes, frozen scientific reference context and actual
execution reports. This is an LLM review, not the reward or an independent
scientific recomputation. Return `accept_for_packaging`, `revise` or `blocked`,
a concise rationale, and actionable issues with evidence.

An undefined public comparison convention is a contract defect if it can change
which submissions pass, even when every executed probe is far from that boundary.
The controller's measured reports, rather than duplicated author-written test
histories, establish current execution outcomes.
Public descriptions of the supplied files must agree with the observed evidence.
A known false input-format or population claim requires correction even when the
fixed instance's outputs happen to be unaffected. Do not downgrade that conflict
to an advisory note merely because current controls pass. Distinguish actual
input observations from assumptions inferred from the reference's parser options.

Independently audit endpoint coverage against `source_evidence`: the original
converted source and narrative, preparation plan and export code. Review all
scientific branches, including results that an earlier worker excluded. Earlier
exclusions are claims to check, not approvals. Preserve all eligible terminal
scientific results in one task. Diagnostic/preparatory results may be excluded
with source-backed reasons; a plot being the only downstream consumer, nested
serialization, inconvenient parsing or a difficult comparison is not itself a
reason to discard an independent scientific result. Check for missing endpoints
in the original source as well as omissions from the preparation inventory.
Apply the current policy for explicitly permitted supplied intermediates: these
can replace an allowed upstream dependency, but cannot give away or remove a
required scientific endpoint. Distinguish such dependencies from independent
endpoints before judging a scientific scope change.

Return this separate source audit in `source_coverage`, using the existing
coverage-review fields: decision, rationale, omitted_scientific_endpoints,
unsupported_evidence_claims, scientific_scope_changes and remaining_validation.
Approve source coverage only with empty defect lists. If an eligible branch is
missing, use `revise` or `blocked` for the overall review even when every executed
control passes. Adding a grader check cannot recover an omitted scientific
branch; if restoring it needs different task construction/reference outputs,
block the candidate rather than approving a smaller task. This source audit
does not establish native isolation, solver performance or publication rights.

Check that all eligible scientific outputs are covered, the public contract
matches executable checks, numerical comparisons have a defensible
precision/serialization basis, identities and cross-file relations are correct,
and meaningful wrong outputs fail without relying on crashes or malformed files.
Check missing values, duplicates, nonfinite values and tolerance boundaries.
Use the host-supplied `artifact_interface` for directory semantics. The grader's
submission argument already names the output root; a declared path is resolved
directly beneath it. In Harbor that root is `/workspace/outputs`. Do not confuse
the solver's `outputs/` directory with an additional layer inside the grader's
argument. Check actual placement from the relative keys in the executed
submission hash records, rather than repeating a candidate's claim about where
its controls ran. Flag conflicting public wording and fallback path searches;
correcting that wording must preserve the controller interface.
Look for answer leakage, hardcoded result shapes/values, control-name detection,
probe flaws, untested equivalences, and shortcuts that merely satisfy this suite.

Successful reference/empty/missing/probe controls are necessary, not sufficient.
Valid representation edits are not independent algorithmic implementations.
The public scientific question defines the target; private API calls are not
additional solver requirements. Keep software choice open, but do not claim
universal portability from a finite set of runs. Check separately what the
original reference, independently executed solution and representation probes
establish. A tolerance chosen to accommodate a wrong scientific method is invalid. Do not repair
science, change selected outputs, or weaken acceptance rules to make controls pass.
A failed/unknown test cannot be described as passing. Distinguish problems with
the proposed public rule from problems with its implementation or a probe.

If `initial_probes` differs from `probes`, the existing repair worker corrected
only expected check IDs, rationale or suite-level concern annotations; mutation scripts and intended overall
pass/fail outcomes must remain unchanged. Verify every correction against the
public scientific rule and actual edit, not merely the grader's observed result.
Do not accept removal of scientific coverage, a weaker challenge, or a relabeled
scientific error. Repaired annotations require fresh execution of all controls;
original failed records remain failures. A scientifically invalid probe script
or intended outcome remains a blocker for this repair path.

Distinguish executed effects from a script's self-reported diagnostics. A vacuous
assertion or dead branch does not establish an effect, but the controller's actual
before/after hashes and reports may establish it independently. Require accurate
annotations of that evidence and its limits; do not require changing a frozen
mutation merely for cosmetic cleanup when its intended effect is established.
Actual invalid mutations or unsupported intended outcomes still block acceptance.

Treat the candidate's prose as claims to check, not as additional experimental
evidence. Verify numerical explanations and margins against the actual controls
and recorded measurements. An arbitrary safety factor is not a precision argument.
Check consequential methodology against the executed source, including omitted
arguments and inherited options. Earlier calls and recommended defaults do not
establish what a later invocation actually used. A public requirement that
contradicts the reference is a contract defect, not grounds to widen a tolerance.
Do not claim that every incorrect method is detected when only particular
counterexamples were executed, or describe two implementations as independent
without checking their provenance. Public rules should explain what is accepted;
keep run-specific calibration measurements and validation history in the private
rationale. Flag contradictions between the original question and the addendum.

An independently executed program is not an oracle merely because the controller
runs it as a comparison control. A requirement to make that control pass cannot
justify changing the scientific question. Disclosing acceptance of unverifiable
extra records or values does not make that acceptance sound. If reconciliation
would require a different question, reference or independent solution, block the
candidate rather than excuse the mismatch as a limitation.

Acceptance here means this grader candidate is suitable for subsequent Harbor
packaging and its own isolation/oracle checks. It does not validate those later
checks, a blind solver, or a release. If revised, affected controls and review
must be repeated on the new candidate; prior evidence stays attached to its hash.

Use the supplied programmatic `control_summary`, checking it against the records,
and cite only mutations those records actually executed. Author-side local-test claims are not additional
controller controls. Check that acceptance-affecting parser/file-size bounds are
publicly disclosed. A stable candidate hash does not excuse misleading wording:
a new corrected version can be validated while the original evidence stays
preserved. Keep instance-specific evidence distinct from general implementation
claims, and report unresolved public-contract mismatches as actionable issues.

## Evidence versions

When `check_description_updates` is present, compare each correction with
`initial_checks`, the current candidate, source evidence and governing public
rules. It may align misleading prose with unchanged scientific requirements;
it must not remove an obligation, relax a criterion or justify an unsupported
equivalence because current controls pass. The controller freezes check IDs,
kinds and artifact coverage, but these structural guards cannot establish
semantic fidelity. Block unsupported scientific changes even when every fresh
control passes. Both original descriptions and the worker's rationale are supplied.

`control_summary` and `controls` describe the freshly executed candidate.
`author_input_control_summary`, when present, records the earlier summary supplied
to the repair author before its submissions were validated. A rationale explicitly
quoting that supplied history should be checked against the earlier summary, not
misattributed to the later results. Do not require an author to predict execution
that occurs after its final submission. This field does not include later tool
feedback; a missing value means no explicit summary is supplied here, not proof
that the author observed no controls. Current executed records remain authoritative.
False scientific claims, invalid probes, failed required outcomes and unresolved
coverage remain blockers; this distinction does not waive any acceptance gate.
