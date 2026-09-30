# Remaining UCSC research captures

Following the user's explicit instruction to archive the remaining files,
this snapshot preserves the liftOver source, downloaded directory/help page
and separate `FOOTER.txt` capture: three original files, 651,361 bytes. The
earlier exclusion was an unresolved review decision; this record preserves
that history without claiming a new upstream permission or changing terms.
The exact [notices](NOTICE.md) and [provenance](provenance.json) travel with
the archived bytes.

This completes the verified public archival of all 73 original cache files.
The first archive and first UCSC
supplement remain unchanged. The separately retained local originals are
also preserved; no chat or worktree is deleted by this operation.

## Reproduction

Run `stage_remaining_ucsc.py` and `archive_cache.py prepare` under
`run_bounded.py` with a 50 MiB estimate. The input is under 1 MiB; processing
is streamed and the estimate covers Python and buffers. Use fresh staging
and snapshot directories. Checkpoint the allowlist, manifest and object plan
before transfer, then use the existing pinned HF environment with the shared
guard, a 400 MiB estimate, and fixed concurrency one. Verify anonymous
downloads of both objects and each archive member. No model calls, biological
data downloads, scientific execution or new paid compute are involved.

## Published outcome

Status: **uploaded and verified by anonymous download**. Inputs were
checkpointed at `8050d9c`; the exact [allowlist](allowlist.json),
[manifest](manifest.json) and [object plan](plan.json) were pushed at
`a417f6f` before transfer.

```text
hf://buckets/open-athena/biotasks/research/3-authoring-migration/2026-09-30/c511d98032fa97c1fab8dcba0bc29da598d3ede61d1d8837018bc4e39a0f7eb0/
```

The first [transfer attempt](transfer-attempt-1.txt) stopped at the shared-node
lock before starting a worker or uploading an object. A subsequent host
snapshot showed low load and ample memory; one guarded retry succeeded.
The [transfer record](transfer.txt) reports exit zero, 1.33 seconds and
57,180 KiB peak RSS. No owned worker remains. The [receipt](verification.json)
confirms anonymous download of both objects and exact sizes/hashes for all
nine members. The archive is 170,995 compressed bytes, 662,061 uncompressed.

The [combined coverage check](coverage-verification.json) rehashed the saved
anonymous downloads for all three snapshots, streamed every archive member,
and matched the union against the original inventory: **73 of 73 original
files, 8,912,921 bytes**, with no missing or duplicate originals. No migrated
cache file remains local-only. Focused Ruff lint and formatting passed for
the staging helper; no supported pipeline code changed.

Preserve all cited snapshots without overwriting them or automatic expiry.
The local copies remain intact, but the migrated evidence no longer depends
on either managed worktree or the separate local retention directory.
