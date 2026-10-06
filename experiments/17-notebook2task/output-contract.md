# Worker output contract v0

All paths below are relative to one isolated author workspace. No worker may
write another worker's evidence or independent validation decisions.

| Artifact | Required content |
| --- | --- |
| `analysis.md` | Source-linked scientific objective, task boundary, solver decisions, assumptions and deviations |
| `input-manifest.json` | Per-input origin/version, SHA-256, size, observed/adapted/simulated/mixed status, transformations, study lineage, access/terms and benchmark-overlap evidence |
| `execution/` | Exact commands, environment, stdout/stderr, exit codes, timestamps, measurements and retained failed attempts |
| `tasks/<id>/proposal.md` | Scientific and grading contract, conventions, tolerances and alternatives |
| `tasks/<id>/task/` | Actual harness-format package, including privately staged reference and grading assets |
| `tasks/<id>/visibility.md` | Solver-visible files and evidence for isolation from solution-bearing assets |
| `checks/` | Submitted artifacts and actual reference/no-op/scientific-error/alternative check results |
| `report.json` | Structured completion or failure report, including partial work |

Blocked jobs may lack task artifacts. Explain missing artifacts in the report;
do not create empty packages and count them as produced tasks.

`report.json` has these required fields. This is a draft contract; no automated
schema validator is implemented yet.

| Field | Value |
| --- | --- |
| `contract_version` | `"v0"` |
| `run_id`, `source_id` | IDs assigned by the runner |
| `status` | `completed`, `blocked`, `failed`, or `budget_exhausted`; completed means author work ended, not independent acceptance |
| `stages` | Object with `retrieval`, `reference_execution`, `task_production`, `author_checks`; each has `status` (`passed`, `failed`, `blocked`, `not_run`), `reason`, and `evidence` paths |
| `tasks` | List of objects with `task_id`, `package_path`, source cell/section lineage, and pending independent acceptance |
| `artifacts` | List of relative path, byte size, and SHA-256 records for retained evidence, excluding this self-referential report |
| `blockers` | List of stage, cause, evidence, and prerequisite needed to resume |
| `scientific_assumptions` | List with supporting evidence, uncertainty, and consequences |
| `source_eligibility` | Separate terms/public-use and evaluation-overlap statuses, evidence, and unresolved questions |
| `repairs` | List of changes, reasons, prior attempt paths, and repeated checks |
| `manual_intervention` | List of external help received; empty for an autonomous job |
| `usage` | Wall time, peak RSS, model tokens, cost amount/currency, telemetry source; unavailable values are null with reasons |
| `independent_validation` | `{"status": "pending"}`; populated later only by independent validation in a separate record |

The runner owns execution status, provider usage/cost, timeout, source/prompt/model
configuration, and environment receipts. Worker-reported usage is supplemental.
Missing/malformed reports are runner failures with retained logs, not zero scores.
Review artifact paths and publication eligibility before archiving; exclude
credentials and do not upload private inputs or traces automatically.
