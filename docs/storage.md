# Research artifact storage

The public [open-athena/biotasks Storage Bucket](https://huggingface.co/buckets/open-athena/biotasks)
holds research snapshots, provider caches, exploratory outputs and run evidence.
Code, prompts, small results, manifests and logbooks stay on permanent research
branches. See [issues](https://github.com/Open-Athena/biotasks/issues) for
experiments and results, including exact artifact locations.

These are operational conventions for preserving research evidence. BioTasks
has no implemented task-release loader or publication pipeline.

Keep large biological data out of the GitHub code repository. Check capacity and
expected transfer costs before uploads, and obtain authorization before unplanned
paid storage or compute. Temporary storage is not a sufficient home for cited
evidence. Preserve source revisions, terms and provenance; public access alone
does not establish permission to redistribute an asset.

## Research bucket snapshots

Use `hf://buckets/open-athena/biotasks/` for research artifacts that should survive a local checkout or temporary directory. Code, prompts, small result tables, manifests and the research logbook remain on the research branch; the issue links the current conclusion and decisive evidence. A bucket upload does not promote an experiment into the established tools or establish task-release readiness.

Maintain the bucket's root `README.md` from [docs/bucket-README.md](bucket-README.md). It describes retrieval and retention conventions; experiment navigation belongs in issues. After publishing a README change, verify its downloaded bytes against the Git source; the Hub renders it below the bucket's file list.

Store a retained snapshot under `research/<issue>-<topic>/<capture-date>/<manifest-sha256>/`. The date is `YYYY-MM-DD`; the final component is the full SHA-256 of the exact manifest bytes. Record the files' paths, byte sizes and SHA-256 hashes, source revisions and provenance, run configuration or a link to it, exclusions, visibility and retention. Record unavailable historical provenance explicitly. Keep the manifest in Git and upload the same bytes alongside the artifacts. Reference the Git manifest by commit permalink, not only a moving research branch.

An archive bundle is useful for a cache of many small files. Preserve each member's path, size and hash in the manifest; record the archive's object path, size and hash in a separate upload plan or receipt. Keep the manifest independent of its own destination and checksum to avoid circular hashing. Use directly addressable files when follow-up work needs selective downloads.

Before uploading, inspect the exact file allowlist, source terms and public visibility; exclude credentials, environments, unrelated files and data that cannot be redistributed. The bucket is public: do not use it as a holding area for private or restricted material, and do not assume that a prefix has separate access controls. Archiving third-party material does not relicense it. Use a separate, explicitly authorized restricted store when needed.

Buckets are mutable and have no Git revisions or built-in version history. Treat retained snapshot prefixes as append-only: refuse overwrites, put corrections under a new manifest hash, and preserve the previous snapshot with an explanation in the logbook. This convention is not server-enforced immutability. Uploads can partially succeed; inspect interrupted transfers before retrying, and never apply a sync deletion operation to a retained snapshot.

Verify a completed upload by downloading it into a fresh directory and checking the recorded sizes and hashes, including archive members. For this public bucket, verify anonymous retrieval as well. Commit the verification result and artifact locations before calling the snapshot archived or closing a migration item. Checksums establish byte integrity; scientific validation and release eligibility are separate checks.

Keep cited snapshots while any research conclusion, issue or release depends on them. Do not automatically delete them when an issue closes or a research branch is archived. Record and review any deliberate retention change, preserve replacement evidence, and update references before removing an artifact. Optional disposable work goes under `scratch/` with a recorded expiry; scratch paths must not be the only copy of cited evidence. Local scratch cleanup is a separate action after archive verification.

Use the [HF bucket CLI or Python API](https://huggingface.co/docs/huggingface_hub/guides/buckets) with normal Hugging Face authentication. Never put tokens in manifests, commands saved to logs, or Git. Record the client version, commands and transfer settings with the research run. Follow the shared-node resource limits in [AGENTS.md](../AGENTS.md); storage transfers also consume memory and CPU. Storage tooling remains experiment-local until a reusable pipeline interface is justified.
