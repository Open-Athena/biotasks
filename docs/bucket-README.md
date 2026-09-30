# BioTasks research artifacts

Public working artifacts for [BioTasks](https://github.com/Open-Athena/biotasks), an open pipeline for generating and independently validating computational biology tasks.

This bucket holds research snapshots, provider caches, exploratory outputs and run evidence. Research code, small results and manifests live in GitHub; questions and conclusions live in [research issues](https://github.com/Open-Athena/biotasks/issues). Eventual task releases will use commit-pinned Hugging Face dataset repositories.

## Contents

| Study | Snapshot | Evidence |
| --- | --- | --- |
| [#5: Discover and prioritize biological task sources](https://github.com/Open-Athena/biotasks/issues/5) | September 29, 2026 provider cache: 950 files, 72,973,920 original bytes; archived September 30 as a 13,587,211-byte gzip bundle | [Manifest and upload plan](https://github.com/Open-Athena/biotasks/tree/8b212cee02252a53e8fa6e54c9d692cac3cf8a4f/experiments/5-source-discovery/runs/2026-09-30-bucket-archive), [anonymous download verification](https://github.com/Open-Athena/biotasks/blob/8b212cee02252a53e8fa6e54c9d692cac3cf8a4f/experiments/5-source-discovery/runs/2026-09-30-bucket-archive/verification.json) |

The first snapshot is under:

```text
research/5-source-discovery/2026-09-29/ecea93611df1d0e65dd3ce05b552f4cea5fba886c8fea2a06402aa59f94207f1/
  manifest.json
  cache.tar.gz
```

The cache preserves original responses, including partial and failed requests. Its contents are research evidence, not a validated task release. Third-party content retains its original source terms; public storage does not grant a new license.

## Retrieve and verify

Use the [HF bucket CLI or Python API](https://huggingface.co/docs/huggingface_hub/guides/buckets). Public downloads do not require authentication. For example, retrieve the manifest first:

```bash
hf buckets cp \
  hf://buckets/open-athena/biotasks/research/5-source-discovery/2026-09-29/ecea93611df1d0e65dd3ce05b552f4cea5fba886c8fea2a06402aa59f94207f1/manifest.json \
  ./manifest.json
```

Compare its SHA-256 with the digest in the snapshot path and the Git-pinned manifest above. Download `cache.tar.gz` from the same prefix and check its size and SHA-256 against the upload plan, then verify member paths, sizes and hashes before using the files. The linked run record includes the verification helper and environment. Checksums establish byte integrity, not scientific validity.

## Storage conventions

- Retained snapshots use `research/<issue>-<topic>/<capture-date>/<manifest-sha256>/`.
- Buckets have no version history. We preserve cited prefixes without overwriting them; corrections get a new manifest hash and a linked explanation.
- Keep cited snapshots while research or releases depend on them. Issue closure does not authorize deletion.
- Disposable work may use `scratch/` with an explicit expiry. It must not be the only copy of cited evidence.
- This bucket is public. Keep credentials and private or restricted data out of it.

See the [project storage guidance](https://github.com/Open-Athena/biotasks/blob/main/docs/storage.md) for maintained policy. This landing page may be updated as the catalog grows; its source is maintained as `docs/bucket-README.md` in the BioTasks repository. The snapshot contents and Git-pinned evidence links remain the reproducibility record.
