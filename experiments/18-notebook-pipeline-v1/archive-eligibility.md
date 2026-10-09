# Public archive review in progress

The destination is the existing public `open-athena/biotasks` bucket. `bucket-preflight.json` records a read-only visibility and size check using huggingface_hub 1.33.0. No files have been uploaded for this experiment. Follow [the repository storage convention](../../docs/storage.md) and the [official bucket API documentation](https://huggingface.co/docs/huggingface_hub/guides/buckets): use an explicit file allowlist, an append-only manifest-hash prefix, and fresh anonymous download verification.

`source-terms-evidence.json` pins repository declarations and their exact bytes under `source-terms/`. These declarations support source review; they do not automatically clear every external biological dataset or generated derivative.

| Seed source | Declaration found at the pinned revision | Remaining asset review |
| --- | --- | --- |
| Scanpy | BSD 3-Clause | Preserve the separately recorded 10x PBMC3k CC BY 4.0 attribution for data and derivatives. |
| Harvard bedtools | MIT | Resolve external BED-file lineage before public data redistribution; preserve the observed build inconsistency. |
| methylKit | Artistic-2.0 in DESCRIPTION | Count-table origin is unresolved; do not describe it as observed or silently treat package licensing as original biological provenance. |
| QFeatures | Artistic-2.0 in DESCRIPTION | The CPTAC table comes from a separate pinned msdata package; preserve its GPL declaration and study attribution. |
| MDAnalysis UserGuide | LICENSE includes LGPL 2.1 and CC BY-SA 4.0 texts | Resolve their applicability to the notebook, and separately preserve the MDAnalysisTests data terms and simulated-trajectory attribution. |
| xcms | GPL 2 or later declaration and notices | Preserve source-package attribution and the faahKO lineage for extracted feature tables. |
| COBRApy | LICENSE contains GPL and LGPL texts | Confirm applicable package and textbook-model terms; do not infer measured-flux provenance. |
| phyloseq | AGPL-3 in DESCRIPTION | Preserve GlobalPatterns source-study attribution and packaged sample identities. |
| scikit-bio tutorials | BSD 3-Clause | Preserve supplied sequence provenance; headers alone do not establish sequence-accession or orthology verification. |
| PyRadiomics | BSD-style three-condition license text | Release image/mask lineage and redistribution scope need separate review. |

The final allowlist must cover exact bytes, including original source notices and modifications where applicable. Exclude credentials, launcher environments, private service endpoints, dependency installations and unrelated files. Check full traces rather than assuming a small summary proves them safe to publish. Any omitted original asset must have a recorded reason, source hash and retained private evidence location. Existing private S3 copies are not a verified public HF snapshot.

The first two Scanpy authoring manifests describe approximately 146 MB and 131 MB of generated files before deduplication, plus input archives and solver evidence. Use streaming hashing and transfers; do not materialize all files into one in-memory archive on the shared VM. File sizes, transfer totals, eligibility and source terms must be frozen before upload. Retain snapshots while cited research depends on them; no automatic deletion after issue closure.
