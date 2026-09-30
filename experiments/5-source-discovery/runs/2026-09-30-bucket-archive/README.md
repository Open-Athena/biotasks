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

## Outcome

The public [bucket](https://huggingface.co/buckets/open-athena/biotasks) was created
and the snapshot uploaded on 2026-09-30. The manifest and upload plan were
checkpointed at `085787999a27b66eaed6088c06260e8e6e49b121` before transfer; the preparation
checkpoint is recorded in the manifest. See [manifest.json](manifest.json),
[plan.json](plan.json), and [verification.json](verification.json).

Anonymous download into a fresh directory verified both objects and all 950
archive members: 72,973,920 original bytes. The gzip archive is 13,587,211 bytes;
the manifest is 159,933 bytes. Every source file matched the prior migration
inventory. The high-confidence credential-pattern scan found no matches; it is
not a complete secret or redistribution review. The archive retains partial
and failed responses as evidence, not successful observations.

The exact prefix is
`hf://buckets/open-athena/biotasks/research/5-source-discovery/2026-09-29/ecea93611df1d0e65dd3ce05b552f4cea5fba886c8fea2a06402aa59f94207f1/`.
It contains `manifest.json` and `cache.tar.gz`; the upload plan records their
SHA-256 values. The digest in the prefix matches the exact manifest bytes.

[Preparation](preparation.txt) exited zero in 3.29 seconds at 22,600 KiB peak
RSS. [Upload and verification](transfer.txt) exited zero in 2.87 seconds at
81,888 KiB peak RSS. [environment.txt](environment.txt) pins the isolated client
environment. The original `/tmp/bio-discovery-20260929` cache remains in place.
No billing plan was changed. This completes the durable archival handoff item;
research continues under issue #5. The original migration inventory remains an
unchanged historical record of its earlier, non-durable state.

## Bucket landing page and main guidance

At the user's request, a root `README.md` was uploaded separately from the
retained snapshot. Its reviewed source is `docs/bucket-README.md` in pipeline
commit `b6d0ad9691ee137e2d7a068d0296082434c187cc`, proposed with the storage and
AGENTS guidance in [PR #8](https://github.com/Open-Athena/biotasks/pull/8) to
`main`. The PR is open, not merged. The bucket README is already published.

[Anonymous readback](readme-verification.json) matched all 3,371 source bytes
and their SHA-256. The [public page check](readme-page-check.json) received HTTP
200 and found the README title and both snapshot/evidence references in the
served HTML. Its [transfer record](readme-transfer.txt) reports exit zero,
0.88 seconds and 54,928 KiB peak RSS. The landing page is a mutable catalog;
it is outside the retained snapshot prefix.

The [focused archive checks](checks.txt) also cross-checked the manifest against
the prior allowlist and the upload receipt, and rejected corrupted, missing,
extra and duplicate members in small synthetic archives. These checks test
byte-integrity behavior, not the science represented by the cache.
