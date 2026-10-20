# Autonomous attempt 005: exploratory input state leaked into setup acceptance

The frozen factory `9e5eb9f05186aed8e513dcf9fa2a8a0e81ebe06a` passed preparation
and a controlled reference test, but fresh replay failed during environment setup.
Read-only inspection of the replay setup log reported a missing staged input: the
recipe expected a file from the earlier exploratory cache. The controller recreated
the Python environment but did not clear either permitted input root before testing
staging. This is an infrastructure/controller failure, not a scientific rejection.

The next general fix empties both input/cache roots before each setup test, requiring
the worker's recipe to stage its own inputs. No generated recipe was manually edited.
The candidate-first construction change was not reached by this run.

Original receipts were recovered with SHA-256 checks. The host terminated with
`FAILED`; provider inventory confirmed zero owned Daytona sandboxes. The recorded
$2 reservation is an allowance, not billed usage.
