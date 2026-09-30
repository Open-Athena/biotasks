# Migration validation — September 30, 2026

Question: can the imported study support follow-up analysis without the Marin
checkout or fresh collection? The saved numeric comparisons reproduce, with
the limits below.

Input checkpoint: `d0e52828229127776a1a5b94b669c711f39e0a5c`. The pinned Marin
source is `249d919641d20cc1a06ac6a7ae84b34848547363`; the BioTasks base is
`c860147af3883e209d9724c7abf4f9c13f337eb9`.

## Evidence

- [Verification output](verification-01.txt): exact imported hashes, saved-input
  ranking/expansion reproduction, independent adoption calculations, and local
  link checks; start/end, exit status, and peak RSS are included.
- [Environment and commands](run.json): Python, uv, lockfile hash, checkpoint,
  working directory, commands, and scope.
- [Historical-hash reconciliation](historical-hash-check.json): three original
  baseline hashes match the pre-correction Marin commit, while the imported bytes
  include the September 30 eligibility review. Both versions remain identifiable.
- [Retained local cache](retained-cache.json): 950 files and 72,973,920 bytes,
  retained at their source location. [Resource record](cache-inventory-resources.txt).

The original analysis functions reproduced both ranking result objects and
tag-frequency tables, plus the expansion result. A separate standard-library
calculation checked 27 adoption comparisons and the outlier sensitivity, using
the saved candidate measurements, pair membership, average ranks for ties,
missing-value handling, and aggregation rules. Counts and identities were exact;
floating coefficients used 1e-12 absolute/relative tolerance. The adoption CSV
and saved topic frequencies/search groups were also checked.

## Limits and remaining work

- Fresh provider responses were not retrieved or verified against all cached
  response hashes. The cache inventory preserves file identities; it does not
  validate upstream factual claims.
- Figures were preserved by hash. Historical plotting helpers were recovered
  but not rerun, and their dependency environment is not locked in BioTasks.
- Eligibility and manual annotations were retained rather than independently
  re-reviewed. Reproducing arithmetic does not establish task quality, dataset
  suitability, or release readiness.
- The raw cache remains in local `/tmp`, which is not durable storage. Keep it
  until an archival destination and retention policy are established. Migration
  #2 stays open for that item; saved-input follow-ups can proceed in issue #5.
- No application code, packaged prompts, dependency pins, or CI configuration
  changed. Validation is specific to the research import; no new GitHub CI or
  application-test result is claimed.
