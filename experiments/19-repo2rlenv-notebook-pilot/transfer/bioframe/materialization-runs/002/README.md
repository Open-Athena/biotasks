# Bioframe construction 002 — provider rejection before submission

The general identity/format guidance was exercised from checkpoint `095a3f1`.
GLM inspected duplicate coordinate keys and conflicting annotations, but did not
submit a task candidate. The stage ended incomplete after **460.90 seconds**:
12 model responses were received; request 13 raised `BadRequestError`. There is
no controlled oracle result, new scientific rejection, solver or release.

A debugging command printed 1,235,651 bytes into its output log. The next saved
request occupies 1,594,921 JSON bytes; the preceding request used 28,907 prompt
tokens. The large output is recorded in the original archive. `output-volume.json`
and the verbatim `last-shell-command.txt` display preserve the evidence linkage.
Context overflow is suspected, but the original error receipt discarded the
provider's explanation; that cause is not yet confirmed. The original ledger's
last slot remains `uncertain` under the old error-handling policy and is not
rewritten here.

A separate diagnostic is prepared to replay that exact hash-verified request
once, without executing returned tools or creating a Daytona sandbox. New error
receipts distinguish a definite HTTP rejection from an uncertain transport and
retain a safe category without copying private response text. These are general
observability changes, not scientific repairs. Tool-output preview policy remains
under discussion; no model input/response/token cap was reintroduced.

The full archive passed download verification. Selected original files are
retained unchanged with their hashes; large requests, responses and tool logs
remain in the configured private archive. The worker reported successful cleanup,
a separate provider lookup confirmed zero owned sandboxes, and the Iris job is
terminal. No generated task, solution, reference or grader was manually patched.
