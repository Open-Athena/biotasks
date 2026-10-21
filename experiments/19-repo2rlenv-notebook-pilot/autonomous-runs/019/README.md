# PyHMMER first placement: no pipeline execution

The submitted host remained pending without a task container beyond its
ten-minute scheduling allowance. Its selected compute peer was unreachable.
Cancellation initially timed out; a subsequent independent status read confirmed
`KILLED`, `Cancelled before handoff`, no start time and zero tasks.

This is an infrastructure outcome, not a notebook rejection or model result.
No orchestrator, model call or Daytona sandbox ran. Original submitted input
identities are preserved in inputs.json. The unused $5 hold can be reassigned
only after that cancellation readback; it was not reassigned on the timed-out
request alone. No original notebook or generated scientific artifact was repaired.
