# Remaining UCSC research captures

Following the user's explicit instruction to archive the remaining files,
this snapshot preserves the liftOver source, downloaded directory/help page
and separate `FOOTER.txt` capture: three original files, 651,361 bytes. The
earlier exclusion was an unresolved review decision; this record preserves
that history without claiming a new upstream permission or changing terms.
The exact [notices](NOTICE.md) and [provenance](provenance.json) travel with
the archived bytes.

This completes the planned public archival of all 73 original cache files
when the transfer has been verified. The first archive and first UCSC
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

Status: preparation inputs recorded; upload pending.
Preserve all cited snapshots without overwriting them or automatic expiry.
