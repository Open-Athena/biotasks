# Autonomous attempt 006: malformed generated exports rejected

Factory `4d25f9ec0f13306abdb7084dc350548c61288c01` completed an unattended rejection.
The notebook analysis ran offline, but its generated export code wrote one filename
that disagreed with the declared artifact inventory. The second controlled test
returned exit 0 for computation while correctly reporting a missing declared file.
The setup worker did not alter the frozen exports; it returned `blocked`, and the
pipeline recorded `rejected`. No operator handoff or generated-artifact edit occurred.
This is rejection of a malformed generated candidate, not evidence of bad science
in the seed. Construction, grading and native solver execution were not reached.

Original receipts were recovered with SHA-256 verification. The host terminated
with `SUCCEEDED`, meaning the rejection workflow completed; it does not mean a
task was validated. Provider inventory confirmed zero owned Daytona sandboxes.
The $1 sandbox reservation is an allowance, not billed usage.

The original worker explanation is preserved unchanged. Its additional claim about
hash placeholders in the preparation plan is unsupported: the actual plan has no
such hash declarations. The filename mismatch is independently established by
`preparation.json` and `reference-test-2.json`; acceptance of the rejection does
not endorse every sentence in the explanation.

Preparation now explicitly reminds workers to keep export filenames and declared
inventory consistent. No file-specific repair or extra preparation call was added.
Future diagnostic exports also retain controller test records automatically.
A further fresh run is needed to exercise candidate-first construction and the
positive scientific/native validation path.
