# Bioframe 192 — source population rejection

Setup and two offline reference replays completed. The specification worker declined to pose a task because the original notebook discards the first motif observation: `read_table(..., schema="jaspar", skiprows=1)` is applied to a staged JASPAR file beginning with a valid seven-field record, not a header. The recorded installed reader defaults to `header=None` and forwards `skiprows` to pandas. A [read-only audit](source-population-audit-192.json) corroborates these exact original records. The impact on each endpoint was not recomputed.

This is an evidence-backed source-fidelity rejection, distinct from a generated grader defect or infrastructure failure. The worker did not silently repair the parsing, accept a changed population, or build a task from the lossy parsed frame. No operator scientific edit, extra repair, construction, grading, solver or publication occurred. [Original worker explanation](../../autonomous-runs/192/specification/specification.json).

The worker also reconsidered three scientific endpoints omitted by preparation, including the reverse overlap question. These are retained model findings, not validated downstream task artifacts. Byte-identical replay establishes repeatability, not scientific correctness.

All 969 science files (36,747,877 bytes) and 30 sealed root files (1,039,687 bytes) were independently read back and hash/size/mode verified. Both original sandbox IDs and owner labels are absent. Pipeline time was 42.93 minutes with 82 recorded request attempts. [Result](result-192.json), [performance](performance-192-detail.json), [cleanup](../../autonomous-runs/192/provider-cleanup.json).
