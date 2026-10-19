# Construction 003: canceled routing mismatch

This campaign was submitted at `dad9f99`, then canceled because the prior-draft
configuration selected the legacy finalization prompt rather than the updated
construction prompt. Iris eventually confirmed KILLED. Its parent had reported
PENDING/no tasks while Daytona already had an owned sandbox, so no claim of zero
model calls or no execution is supported. No recovery manifest or accepted task
was retrieved. This is an operator/configuration failure, not a scientific result.

The replacement separates prior-file input from authoring-mode selection; the
generic constructor can inspect inputs while reusing unchanged worker code.

The owned sandbox was explicitly deleted after worker cancellation. Independent
provider readback at 23:03:13 UTC confirmed zero remaining campaign sandboxes.
