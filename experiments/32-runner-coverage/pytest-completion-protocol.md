# Explicit pytest completion candidate

This supersedes the outer-only check for the next pytest comparison, while preserving that earlier source and evidence. The actual-shell counterexample showed that a final successful marker echo hides an inner pytest interruption. The new native candidate fails on setup/reset/patch errors, records the test block's status immediately, prints it on a guaranteed separate line, and requires exactly one ordered start/status/end sequence with completed transport and pytest exit 0 or 1. Ordinary assertion failures remain valid for the pre-fix stage. The original test commands, per-test IDs and test patch are not weakened or narrowed.

Native and standalone exported pytest parsers share the same previously checked SGR normalization. The exported grader checks the recorded pytest exit before awarding reward: exits outside 0/1 yield zero reward and unresolved/unclean status even if useful-looking test lines were parsed. This is an experimental grading change, not a regrading of any original record. The earlier SGR-only grader is retained for comparison.

The strict native candidate explicitly skips non-pytest/unknown commands. This is a declared research limitation for the Python cases, not general runner coverage or a replacement suitable for all upstream pipelines. Runner-aware contracts for SAMtools and other conventions remain open. Arbitrary bootstrap commands can themselves mask a program exit; capturing the shell block's code cannot prove the behavior of arbitrary wrappers. Exported setup/reset semantics are unchanged here; #31 separately investigates their correctness. No pipeline promotion or biological task recovery is claimed.

## Executed checks

`check_pytest_completion.py` runs real pytest with forced ANSI color through actual Bash/Git in a small synthetic repository. Six native cases cover the complete pair, keyboard interruption, explicit exit124, SIGKILL, invalid base and invalid test patch. The complete case preserves exactly one F2P and two P2P IDs, pre-exit1 and post-exit0; error cases stop after the affected first stage. An unsupported-runner check verifies an explicit skip before execution. Five controlled marker/transport checks reject missing/duplicate/reversed markers, no-tests exit5 and a nonzero outer exit.

Five standalone-export checks read output from real pytest executions. Nop/oracle remain reward0/1 under both SGR-only and completed-exit graders. Keyboard interruption, explicit exit124 and SIGKILL have parsed partial results: the SGR-only grader awards0.5, while the completed-exit grader gives0 and marks the run incomplete. Exit124 is a forced runner exit in this fixture, not a wall-clock timeout benchmark. No original task files or rewards are used.

The first fixture attempt correctly stopped at a read-only global Git configuration path; the harness was then isolated with a temporary `GIT_CONFIG_GLOBAL`, without changing source-stage semantics or touching user configuration. A later failure exposed missing newline separation after an abruptly terminated runner; the candidate was fixed to print a leading newline before its status marker. Failed resource records are retained separately. The final check uses2.46seconds and43,824KiB peak RSS, returns0, and removes its temporary directory. No model calls, network access or remote jobs.

## Next evidence boundary

Before live acceptance claims, bind this combined candidate to frozen repository inputs and compare complete native results plus exported controls where recovery is claimed. Do not relabel retained partial MNE logs as valid tasks. Preserve the older candidate outcomes, original task contracts and independent resource/cleanup accounting.
