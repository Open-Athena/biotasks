Additional controller guidance for notebook-derived scientific tasks:

Choose semantic probes that discriminate on the actual fixed inputs. A changed
comparison operator, order of operations or parameter can produce identical
outputs when the relevant data are absent. Do not assume a boundary case exists.
Before selecting a wrong-solution probe, explain why its change affects a graded
scientific quantity on these inputs by more than the allowed tolerance. Prefer
a clear, demonstrable scientific error over a hypothetical edge case.

The probe must construct observably incorrect submission artifacts, preserving
the original data, private tests, reward machinery and reference implementation.
Do not weaken the verifier or change the task to force rejection of an equivalent
output. Preserve failures and follow the upstream rules for immutable controls.

A valid alternative must independently implement the public methodology, keeping
identifiers and data parsing correct. Software and storage representation may
differ when the task permits it. Distinguish a broken probe from a task defect.

Use only short, exact, contiguous citations from available documents. Explain
inferences outside quotes; never use ellipses or reconstruct quoted JSON fields.

Treat undocumented output representation constraints as contract defects, not
optional improvements merely because one alternative passed. Check whether
scientifically equivalent identifier/order representations are permitted by the
public contract and handled by the grader. Clarify genuinely required output
fields; do not invent a scientific reason for arbitrary implementation choices.

Check the actual solver privileges and verifier environment. File mode bits do
not make reference inputs immutable to a root solver. When expected results are
computed from solver-visible data, require independently validated source identity
or an isolated trusted reference copy before computing those expectations. Do not
infer protection from a comment, path name, or chmod command. Any repair must be
your own proposal through the existing repair mechanism; preserve the biological
methodology and installed semantic controls.
