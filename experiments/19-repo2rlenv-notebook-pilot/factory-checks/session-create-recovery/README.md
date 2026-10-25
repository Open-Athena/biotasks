# Pre-command session creation recovery

A lost session-creation response is distinct from a lost command submission. Before any execute call, the wrapper may reconcile the same identified empty session or make one creation retry after a definite404. It never repeats an execute submission, and all operations share the original deadline. Unknown, mismatched or nonempty sessions still stop the operation.

The [original158failure](../../panel-rounds/047/failure-158.md) stopped before a command was submitted. The first synthetic provider check recovered an existing empty session and observed exactly one execution; the next missing-session case stopped safely because the SDK returned a not-found subclass rather than the exact base class name. The complete original failure and cleanup remain preserved. The corrected base-class check passes140affected local tests. A separately funded002provider check is pending; this is not a notebook-validation claim.

The earlier launcher import failure occurred before any provider sandbox creation and is preserved privately. No scientific task, method, input, model, deadline, or repair allowance changed.
