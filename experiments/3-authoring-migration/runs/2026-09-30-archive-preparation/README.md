# Public authoring archive

Status: **uploaded and verified by anonymous download**. The exact
[allowlist](allowlist.json), [manifest](manifest.json) and [object plan](plan.json)
were checkpointed before publication. The source cache remains intact.

The bundle contains 67 original local files (8,226,706 bytes), eleven license
and provenance files, and [NOTICE.md](NOTICE.md): 79 members totaling 8,295,341
bytes. The compressed archive is 3,789,136 bytes. This includes raw execution
logs, preparation/checking helpers and cache evidence, with failed launches
and the service-blocked partial run preserved. It is not a model/scientific run.

The remaining six local files (686,215 bytes) are explicitly retained at source
in `allowlist.json` and `manifest.json`. They are the UCSC README, liftOver
source, two utility source files, and downloaded directory/help pages. The
liftOver override has custom terms; the rest need file-specific review before
public redistribution. Neither durable external archival of those six files
nor permission to delete the originals is claimed. The migration's
retained-at-source disposition is explicit, rather than silently treating the
files as archived. [Four source files](retained-upstream.json) also match the
Git blobs at their pinned upstream revision; the directory/help pages remain
local-only mutable-source captures. Upstream availability is not controlled by
BioTasks. Any later public archival needs a new reviewed allowlist and prefix.

Later retention update: all six excluded files now also have a
[verified private copy outside managed worktrees](../2026-09-30-worktree-retention/README.md).
The source worktree is no longer their only local copy. Preserve that separate
copy if the old chat/worktree is removed; these bytes remain outside public HF
storage and are not backed up off this VM.

## Preparation and provenance

The staging and archive inputs were checkpointed at
`3aef93310e4be3255e8df30f748b9b626a7631d8`. The wrapper is adapted from the
[discovery migration helper](https://github.com/Open-Athena/biotasks/blob/6bb14ef5eea9a58b6b704808ff21bdecb8791170/experiments/5-source-discovery/scripts/archive_cache.py).
Changes record this study's issue, source provenance, license review and prefix;
transfer requires the existing public bucket and never creates one or changes
visibility. It refuses a populated snapshot prefix. No deletion or overwrite
operation is used.

[Staging](staging.txt) exited zero in 0.04 seconds at 16,836 KiB peak RSS.
[Preparation](preparation.txt) exited zero in 0.46 seconds at 22,020 KiB. It
checked every staged hash, scanned for high-confidence credential patterns,
created a deterministic gzip/tar bundle, and streamed all 79 archive members
back to verify exact membership, sizes and hashes. The raw CLI event streams
contained no reasoning items. These observations do not amount to a general
secret audit or establish rights to biological assets merely referenced by
the research.

The published append-only destination is:

```text
hf://buckets/open-athena/biotasks/research/3-authoring-migration/2026-09-30/5ae7ab3aad02c42236362cb9fe0ca5b685906a8e00d720fd9c6cf96a46993e0b/
```

It contains `manifest.json` and `cache.tar.gz`. The prefix is the exact
manifest SHA-256; this is an operational convention for an unversioned bucket.
The local prepared snapshot is
`/tmp/biotasks-authoring-archive-01a0f412/snapshot/`.

## Publication procedure

The exact manifest and plan were published at checkpoint
`d65f65b08932edec177701aa8b325cb60574919a` before transfer. Use
the pinned `huggingface_hub==1.6.0`, `hf-xet==1.6.0` environment recorded in
[transfer-environment.txt](transfer-environment.txt). Run one transfer under
the shared-node guard with a 400 MiB estimate, less than ten minutes, fixed
concurrency one and bounded Xet buffers. The small archive, Python/SDK overhead
and buffers fit that estimate; the guard monitors the real resource limits.

```bash
python3 experiments/3-authoring-migration/scripts/run_bounded.py 400 \
  /tmp/biotasks-hf-archive.uVSXzq/venv/bin/python \
  experiments/3-authoring-migration/scripts/archive_cache.py transfer \
  /tmp/biotasks-authoring-archive-01a0f412/snapshot \
  /tmp/biotasks-authoring-archive-01a0f412/download \
  experiments/3-authoring-migration/runs/2026-09-30-archive-preparation/verification.json
```

The helper uses normal HF authentication without recording token values, then
downloads both objects anonymously into a new directory and verifies every
member. Stop on quota or resource errors; changing a billing plan is outside
scope. Inspect partial transfers before retrying; `--verify-only` supports
read-only recovery. Commit the receipt and transfer/resource record before
claiming archival. Preserve the source and cited snapshot while conclusions
depend on them. Bucket README changes are separate mutable catalog updates.

## Outcome

[Anonymous verification](verification.json) downloaded both objects and matched
every size/hash and all 79 archive members. The [transfer record](transfer.txt)
reports exit zero, 1.77 seconds and 62,672 KiB peak RSS. The bucket remained
public; no billing plan or visibility setting changed. No cache file was
deleted. Six excluded UCSC files retain the disposition described above.
