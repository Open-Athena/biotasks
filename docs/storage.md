# Storage and public publication

[Planning overview](README.md) · [Validation](validation.md)

The project is public by default. Publish documentation, prompts, generation code, eligible inputs, references, graders and validation evidence. Research artifacts use the public [open-athena/biotasks Storage Bucket](https://huggingface.co/buckets/open-athena/biotasks). The dataset repository and exact layout for task releases are not yet selected.

## Storage roles

| Artifact | Home |
| --- | --- |
| Planning docs, prompts, schemas, generation code and small manifests | [Open-Athena/biotasks](https://github.com/Open-Athena/biotasks) |
| Research snapshots, provider caches, exploratory outputs and detailed run evidence | The public `open-athena/biotasks` Hugging Face Storage Bucket; exact paths and hashes recorded in Git |
| Released Harbor task packages and biological input assets | Planned: a public Hugging Face dataset repository, pinned by commit for each release |
| Reference solutions, grading assets and release validation summaries | Public versioned artifacts alongside the release, separated from solver input assembly |
| Temporary downloads, build intermediates and detailed validation outputs | Object storage near the authoring compute, with a retention policy; regional GCS for TRC work |
| Public example and coverage pages | Version-controlled static HTML, previewable from GitHub; links to the exact release and evidence |

Hugging Face dataset repositories provide versioned distribution for releases; [Storage Buckets](https://huggingface.co/docs/hub/storage-buckets) hold working research assets without Git history. Account [storage limits](https://huggingface.co/docs/hub/storage-limits) apply to both; public storage is not unlimited. Check capacity and expected transfer costs before large uploads, and obtain authorization before unplanned paid storage or compute.

Transient object storage is not the sole location of release evidence. Promote accepted task artifacts and the evidence needed to reproduce them into the public release. Keep large biological data out of the GitHub code repository. Do not repeatedly copy raw archives when a task needs only a scientifically valid subset or upstream-produced matrix.

## Research bucket snapshots

Use `hf://buckets/open-athena/biotasks/` for research artifacts that should survive a local checkout or temporary directory. Code, prompts, small result tables, manifests and the research logbook remain on the research branch; the issue links the current conclusion and decisive evidence. A bucket upload does not promote an experiment into the supported pipeline or establish task-release readiness.

Maintain the bucket's root `README.md` from [docs/bucket-README.md](bucket-README.md). It is a navigational catalog that may be updated, separate from retained snapshot evidence. After publishing a README change, verify its downloaded bytes against the Git source; the Hub renders it below the bucket's file list.

Store a retained snapshot under `research/<issue>-<topic>/<capture-date>/<manifest-sha256>/`. The date is `YYYY-MM-DD`; the final component is the full SHA-256 of the exact manifest bytes. Record the files' paths, byte sizes and SHA-256 hashes, source revisions and provenance, run configuration or a link to it, exclusions, visibility and retention. Record unavailable historical provenance explicitly. Keep the manifest in Git and upload the same bytes alongside the artifacts. Reference the Git manifest by commit permalink, not only a moving research branch.

An archive bundle is useful for a cache of many small files. Preserve each member's path, size and hash in the manifest; record the archive's object path, size and hash in a separate upload plan or receipt. Keep the manifest independent of its own destination and checksum to avoid circular hashing. Use directly addressable files when follow-up work needs selective downloads.

Before uploading, inspect the exact file allowlist, source terms and public visibility; exclude credentials, environments, unrelated files and data that cannot be redistributed. The bucket is public: do not use it as a holding area for private or restricted material, and do not assume that a prefix has separate access controls. Archiving third-party material does not relicense it. Use a separate, explicitly authorized restricted store when needed.

Buckets are mutable and have no Git revisions or built-in version history. Treat retained snapshot prefixes as append-only: refuse overwrites, put corrections under a new manifest hash, and preserve the previous snapshot with an explanation in the logbook. This convention is not server-enforced immutability. Uploads can partially succeed; inspect interrupted transfers before retrying, and never apply a sync deletion operation to a retained snapshot.

Verify a completed upload by downloading it into a fresh directory and checking the recorded sizes and hashes, including archive members. For this public bucket, verify anonymous retrieval as well. Commit the verification result and artifact locations before calling the snapshot archived or closing a migration item. Checksums establish byte integrity; scientific validation and release eligibility are separate checks.

Keep cited snapshots while any research conclusion, issue or release depends on them. Do not automatically delete them when an issue closes or a research branch is archived. Record and review any deliberate retention change, preserve replacement evidence, and update references before removing an artifact. Optional disposable work goes under `scratch/` with a recorded expiry; scratch paths must not be the only copy of cited evidence. Local scratch cleanup is a separate action after archive verification.

Use the [HF bucket CLI or Python API](https://huggingface.co/docs/huggingface_hub/guides/buckets) with normal Hugging Face authentication. Never put tokens in manifests, commands saved to logs, or Git. Record the client version, commands and transfer settings with the research run. Follow the shared-node resource limits in [AGENTS.md](../AGENTS.md); storage transfers also consume memory and CPU. Storage tooling remains experiment-local until a reusable pipeline interface is justified.

## Release manifest and loading

For each release, record the generation-code commit, task IDs and versions, source accessions, transformations, environment references, asset locations, byte sizes, content hashes, licenses and validation records. Pin Hugging Face downloads by immutable repository revision rather than a moving branch. Preserve revisions used by released manifests.

Include the [instance relationships](task-authoring.md#recipe-variation-and-instance-relationships): operation and scientific-context labels, recipe IDs and versions, component references where used, study and input-asset IDs, generation parameters and derivation links. Downstream users choose their own grouping and splits from this metadata; releases do not assign splits.

The loader should select a task, stage only its required assets, verify their hashes and assemble the Harbor package before solving starts. Shared assets may be cached by content hash; task loading must not require downloading the whole corpus. The exact layout must be tested with the supported Harbor loader before publication.

## Public artifacts and solver isolation

Public availability and solver visibility are different properties. Oracles, expected results and grader code may be public for audit and reuse while remaining absent from solver-visible inputs. Assemble the sandbox from an explicit allowlist; do not mount the entire authoring repository or release archive. Execute grading in a trusted environment that solver writes cannot change.

The default offline task environment prevents live retrieval of public reference files during a solve. Before releasing a network-enabled task, demonstrate controls that preserve its input boundary and prevent retrieval of its public oracle or expected answers; otherwise retain offline staging or defer it. Data splitting and downstream evaluation design remain outside this project.

## Release eligibility

Record source terms and establish permission to redistribute each included input and supporting asset. Check applicable licenses, access conditions and any stated consent or use restrictions. A public download alone is insufficient evidence. Prefer sources compatible with a public corpus; hold or reject candidates with unresolved eligibility.

Public-by-default does not include credentials or third-party private communications. Publish the reusable design and evidence without copying internal service details. Do not silently move existing restricted archives into public storage; construct and validate the intended public release explicitly.
