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

## Published outcome

Status: **uploaded and verified by anonymous download**. Executable inputs were
checkpointed at `7163261`; the exact [allowlist](allowlist.json),
[manifest](manifest.json) and [plan](plan.json) were published at `0c958f0`
before transfer. The original snapshot remains unchanged.

```text
hf://buckets/open-athena/biotasks/research/3-authoring-migration/2026-09-30/1e8e1a890a62529cdcf69200769fb1c5fa7bd4aefb37f62611d3996ae66c73e5/
```

The [receipt](verification.json) confirms anonymous download of both objects,
matching sizes and hashes, and all seven members: three source files and four
license/provenance/notice files. The compressed archive is 14,037 bytes;
uncompressed contents total 43,782 bytes. The [transfer record](transfer.txt)
reports exit zero, 1.30 seconds and 56,856 KiB peak RSS. No worker remains.
Focused Ruff lint and formatting checks passed for both experiment helpers;
the staging and archive checks verified the actual retained bytes.

Together, the original archive and supplement preserve 70 of the 73 original
cache files publicly (8,261,560 bytes). The remaining three files total
651,361 bytes and have a verified private copy outside managed worktrees.
That copy survives source-worktree deletion but is not backed up off this VM.
Preserve the original snapshot, this append-only supplement and the private
copy while cited.

Final retention update: the user subsequently instructed archival of the
[remaining three UCSC files](../2026-09-30-ucsc-remaining/README.md). That
separate snapshot has now been verified anonymously. All 73 original cache
files are publicly archived with their notices; none remains local-only.
The counts and exclusions above describe this first supplement's publication.
