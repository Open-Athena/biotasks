# COBRApy first author session: orchestration timeout

The controller reports FAILED with `Execution timeout exceeded`. It started the task at 17:14:13 UTC and ended it at 17:44:47 UTC. All 40 permitted GLM request/response pairs are present, with HTTP 200 responses. No provider token usage was exported in those proxy log lines.

No final worker archive, task manifest, author trajectory or resource probe was emitted. The controller also reports no retained task output archive. The underlying point of the stall is unknown: these logs do not prove whether ZCode was still exiting or object-storage export was blocked. Partial objects in private run storage have not yet been inspected. No candidate is accepted and no biological reference, grader or solver outcome can be claimed from the available evidence.

An explicit budget-stop check was prepared after the orchestration deadline; by the time it ran, the controller had already marked the job FAILED. No manual cancellation and no automatic retry occurred. One author session remains under the per-seed budget, but a repair requires its own checkpointed review/specification.

Later workers have an explicit stop on a rejected over-budget request and a separately checksummed text checkpoint before storage export. Those changes do not retroactively recover or validate this run.
