# BioTasks research artifacts

Public working artifacts for [BioTasks](https://github.com/Open-Athena/biotasks),
an open project developing tools for creating and validating computational
biology tasks.

This bucket holds research snapshots, provider caches, exploratory outputs and
run evidence. Code, small results and manifests live on permanent research
branches. See [issues](https://github.com/Open-Athena/biotasks/issues) for
experiments and results, including exact snapshot paths, Git-pinned manifests,
upload plans and verification receipts. Bucket contents are research evidence,
not validated task releases. Third-party content retains its source terms.

## Retrieve and verify

Use the [HF bucket CLI or Python API](https://huggingface.co/docs/huggingface_hub/guides/buckets).
Find the snapshot path and pinned manifest in the relevant experiment issue.
Retained snapshots use this layout:

```text
research/<issue>-<topic>/<capture-date>/<manifest-sha256>/
```

Download the manifest first. Compare its SHA-256 with the digest in the snapshot
path and its Git-pinned copy. Check downloaded objects against recorded sizes and
hashes; for archive bundles, also check every member against the manifest. Use the
experiment's upload plan or receipt for the archive object's size and checksum.
Checksums establish byte integrity, not scientific validity.

## Storage conventions

- Buckets have no version history. Preserve cited prefixes without overwriting
  them; corrections get a new manifest hash and a linked explanation.
- Keep cited snapshots while research or releases depend on them. Issue closure
  does not authorize deletion.
- Disposable work may use `scratch/` with an explicit expiry. It must not be the
  only copy of cited evidence.
- This bucket is public. Keep credentials and private or restricted data out of it.

See the [project storage guidance](https://github.com/Open-Athena/biotasks/blob/main/docs/storage.md)
for maintained policy. This landing page's source is `docs/bucket-README.md` in
the BioTasks repository. After publishing an update, verify its downloaded bytes
against that source. Snapshot contents and Git-pinned evidence remain the
reproducibility record.
