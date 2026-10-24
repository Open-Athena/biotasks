Controller timing snapshot: approximately {{REMAINING_SECONDS}} seconds remain
before this worker's fixed deadline. Model latency and tool use consume that
same time. Each model request is limited to {{REQUEST_TIMEOUT_SECONDS}} seconds
or the remaining time, whichever is shorter. Retries preserve the deadline.

Use targeted checks, then return a supported artifact or a specific blocker.
Required validation still applies; do not claim results that have not executed.
