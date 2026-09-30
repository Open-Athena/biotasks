# UCSC archive correction

The original archive conservatively excluded all six UCSC cache files. That
was too broad: the pinned root license covers the repository README, and the
explicit MIT license in `src/utils/LICENSE` covers both cached utility sources.
This supplemental snapshot preserves these three original files with their
copyright and license notices. It does not change the original archive or its
historical manifest.

The source revision is `ad6dd2177ad20bea9e32563ee76a1c598bccb6d5`.
The three source files already matched pinned Git blobs in the
[original upstream check](../2026-09-30-archive-preparation/retained-upstream.json).
[Provenance](provenance.json) records those matches and the exact license
paths. The root license's subdirectory exceptions are preserved, not replaced
by the utilities' MIT license or BioTasks' own license.

The liftOver source has a custom license; the other two captures combine a
directory listing and help text for multiple tools. This review has not
established a public redistribution grant for those three complete files.
That is an unresolved scope question, not a claim that HF prohibits UCSC
content or that every non-commercial license prohibits archival. All six
original files have a [verified local copy outside managed worktrees](../2026-09-30-worktree-retention/README.md).

## Reproduction and retention

Run `stage_ucsc_supplement.py` under the shared-node guard with a 50 MiB
estimate, then `archive_cache.py prepare` with the generated allowlist and a
fresh snapshot directory. The staged source is only 34,854 bytes plus notices;
the estimate covers Python and streaming buffers. Checkpoint the allowlist,
manifest and plan before transfer. Use the existing pinned HF environment
and guarded transfer command, with a 400 MiB estimate and concurrency one.
Download both objects anonymously and verify every member before claiming
publication. No model calls or scientific execution are involved.

Status: inputs checkpointed for preparation; no supplemental upload yet.
Preserve the original snapshot and this append-only supplement while cited.
