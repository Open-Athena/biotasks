# Native verifier cancellation diagnostic

Finite control passed: `True`; native timeout observed: `True`; fixture mechanism observed: `False`.

| Case | Native trial exception | Starts / ends | Live prior writers | In-container hole samples | Final NUL bytes |
| --- | --- | --- | --- | --- | --- |
| finite | None | 1 / 1 | 0 | 0 | 0 |
| timeout | VerifierTimeoutError | 2 / 0 | 1 | 11 | 0 |

This is a self-authored infrastructure fixture through unchanged Harbor 0.6.6, not a biological control rerun, task export or solver score. Five-second verifier deadlines deliberately expose native cancellation/retry behavior; finite and timeout writers run for two and thirty seconds respectively. The trial must both establish its finite control and preserve independent resource/process observations before the mechanism is counted.

The timeout retry began 5.859766 seconds after the first writer. That first PID was still sleeping, with matching start ticks and the same log inode: old descriptor offset 60,416 bytes, new offset zero. Eleven samples measured transient NUL holes inside the task container (maximum 59,392 bytes, from 5.906751 through 10.912932 seconds). The final archived log has zero NULs. Fixed-size writes and measured offsets are consistent with the new writer filling the initial gap. The predeclared conjunction additionally requires final saved NULs, so it remains false; component observations are reported separately as post-run analysis without changing that metric.

Historical Scanpy causation remains unproven. Its missing rewards, old NUL holes, dependency failures and task validity are separate questions. This fixture demonstrates live process survival into retry and transient in-container holes on one worker; it does not reproduce persistent holes in the final saved log. Intermediate snapshots were sampled as counts/hashes, not retained as complete raw files.

Prior preparation attempts used 0.060595556 CPU-hours; this attempt used 0.077063889. Total main allocation 0.137659444 / 1 CPU-hour. The constructor failure and Compose rejection are separately archived, not negative mechanism results. Zero model calls/new paid capacity. Raw evidence, anonymous HF readback and owned cleanup are verified; keep issue open for user review.

Runtime snapshot: `hf://buckets/open-athena/biotasks/research/41-verifier-cancellation/2026-10-24/60c0b5ad39dcd11ff20ab5ca98d0520af1eb4998404aee7618ad922bc3a8b4c9`.
