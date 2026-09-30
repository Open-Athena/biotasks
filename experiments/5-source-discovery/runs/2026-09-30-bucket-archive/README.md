# Durable cache archive

Archive the 950 files (72,973,920 bytes) identified by the
[migration inventory](../2026-09-30-migration/retained-cache.json) in the
`open-athena/biotasks` Hugging Face Storage Bucket. Preserve the original
inventory and source cache; archival does not change the scientific baseline.

Scope: public archival of the existing cache, local preparation, one upload and
download verification, then a focused storage-documentation PR to `main`.
No new provider collection, model calls, scientific analyses, paid compute,
billing-plan changes, or local source deletion. The user explicitly requested public bucket visibility. Archival preserves
source material and does not grant a new license to third-party content; original
source terms still apply.

The executable helper is `../../scripts/archive_cache.py`. Run it from the
repository root under `../../scripts/run_bounded.py`. `prepare` takes the old
inventory and a new local snapshot directory. It rechecks the allowlist, scans
high-confidence credential patterns without printing values, produces a
deterministic gzip/tar bundle, and verifies every member. It writes
`manifest.json` and `plan.json`; the SHA-256 of the exact manifest bytes names
the bucket prefix. Commit these small files before transfer.

`transfer` takes the snapshot directory, a new download directory, and a receipt
path. It creates the public bucket if absent, refuses a populated prefix,
uploads the archive and then its manifest, downloads both into the new
directory, and verifies object hashes and every archive member without
extracting it. `--verify-only` supports read-only verification after an
interrupted run. Partial uploads require inspection; no automatic overwrite or
cleanup is performed. Concurrent writers to this prefix are outside this
one-off helper's contract.

Environment: Python 3.13.13, isolated `huggingface_hub==1.6.0` and `hf-xet==1.6.0`;
the complete environment is recorded alongside the outcome. No new BioTasks
runtime dependency. Authentication uses `HF_TOKEN` or the existing standard HF
token file in-process; credential values are never recorded.

Budget: one worker under the shared lock, less than ten minutes, preparation
estimated at 100 MiB and transfer at 400 MiB. Preparation streams data in 1 MiB
chunks. Transfer sends one compressed object at a time, with fixed concurrency
one, 64 MB download-buffer limit and 16 MB shard-index limit; the estimate
allows for the small archive, Python/SDK overhead, upload buffering and native
libraries. The shared resource guard records timing, exit status and peak RSS.
The [documented Xet settings](https://huggingface.co/docs/hub/xet/using-xet-storage)
are recorded in the verification receipt. Stop on resource thresholds or quota
errors; do not upgrade storage plans automatically.

Checksums establish byte integrity, not scientific validity, completeness of
credential review, or redistribution permission. HF buckets are mutable and
unversioned: retention and append-only prefixes are project conventions, not
server-enforced immutability. Preserve cited snapshots while their evidence is
referenced; record any deliberate retention change.
