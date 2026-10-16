# Validation handoff (all rules proposed, not validated)

**Status.** One recorded reference run + structural audit only; `semantic_fidelity_validated` = false. No tolerance values are asserted anywhere — only comparison families and the evidence needed to set them. Measured facts are cited; everything else is proposal.

## 1. Input materialization (proposed — NOT yet built or validated)

### `inputs/cell_groups.csv`
Source: reference artifact `cell_clusters_umap.csv` (sha256 6f2fc91d14c144f7b7ffc852766318d1dec0acc0312a2e28c08007ce488d7d4d). Keep `sample` and `cluster` (= `leiden_res_0.50`); recover the raw 10x barcode from `cell_id`. Recovery rule (based on recorded anndata uniquify semantics — later duplicates get `-1` appended, concatenated in dict order s1d1→s1d3 — and on the fixed barcode format `<16nt>-1`): s1d1 rows verbatim; s1d3 rows whose `cell_id` ends in `-1-1` have one trailing `-1` stripped; all other rows verbatim. Validations before release: (a) every (`sample`, `barcode`) unique; (b) each barcode present in that sample's h5 barcode list; (c) row count and per-cluster counts unchanged vs the source artifact; (d) the inverse rule reproduces the source `cell_id` set; (e) no columns other than sample/barcode/cluster. Fallback if (b)/(d) fails: key cells by (`sample`, position index in that sample's h5 `barcodes` dataset) instead of string parsing. Withhold UMAP coordinates, other resolutions and `cell_type_lvl1`.

### `inputs/gene_identities.csv`
Build by replaying the recorded read convention offline on the staged h5 files (scanpy 1.12.4 `read_10x_h5` defaults → Gene Expression features in stored order; per-sample `var_names_make_unique`): one row per (sample, GEX feature) with (`sample`, `h5_row` = stored feature index, `gene_id` = post-dedup var name, `ensembl_id`, `gene_symbol`). Validations: (a) `gene_id` unique per sample; (b) `ensembl_id`/`gene_symbol` match the h5 `features` fields at `h5_row`; (c) `gene_id` = `gene_symbol` up to the dedup suffix; (d) map size equals the file's GEX feature count (also records whether non-GEX features exist in the files); (e) both samples present. Fallback: any unreconcilable feature is documented and re-reviewed. Cross-checks to record: number of pooled `gene_id`s whose `ensembl_id` differs between samples (provenance only — the join stays identifier-based, mirroring the reference's var-name inner join).

### Pinning
Record sha256 of both derived inputs; h5 files already pinned (322c30a7…, ca40b287…, provider md5s verified at staging).

## 2. Grading reference (existing, private)

`rank_genes_groups_leiden_res_0.50.csv` (sha256 33aae2d3…; exactly the endpoint produced by `inputs/exports.py`: complete cluster × gene cross product, 17 blocks × 23,427 genes, fields group/names/scores/pvals_adj/pvals/logfoldchanges) plus `rank_genes_groups_params.json` (reference=rest, wilcoxon, use_raw=false, layer=null, BH). Column mapping: cluster↔group, gene↔names, score↔scores, pval↔pvals, pval_adj↔pvals_adj, log2fc↔logfoldchanges; rank = position within a block. Structural pre-checks at validation (no new science): (a) per-block row counts equal; (b) block group order strictly ascending numerically — if not, restate the public sort rule to match (currently "ascending numeric cluster"); (c) within-block scores non-increasing; (d) count of exact score ties within blocks.

## 3. Proposed comparison families (calibrate before finalizing; no numbers)

- **Structural**: single file; exact header; complete cross product (every supplied cluster × every tested gene, once); equal per-cluster row counts; ranks 1..m; score non-increasing in rank; no missing/nonfinite; underflow zeros only in pval/pval_adj.
- **Identity/coverage**: {(cluster, gene)} key set equality with the reference table (multiplicity 1); cluster labels verbatim from the supplied input.
- **score, log2fc**: absolute-plus-relative tolerance family over keyed rows. Calibration evidence required: measured deviation of (i) an independent float64 clean-room implementation from the recorded CSV (sources: float32 rounding of scores/log2fc; expm1/epsilon evaluation order) and (ii) a repeat reference run from itself. The tolerance must separate the largest measured correct-implementation deviation from the smallest measured discriminator effect (§4); if they overlap, the target/comparison is unresolved and must be re-scoped, not silently widened.
- **pval, pval_adj**: log-scale deviation family for values nonzero on both sides; exact-equality family when both underflow to 0. Decide between log-scale closeness of nonzero p vs collapsing only below the smallest positive double. Calibration evidence: distribution of nonzero p magnitudes and exact-zero counts in the reference table; propagation of small p deviations through BH (pval_adj is a deterministic monotone function of the within-cluster p vector — do not assume common-factor rescaling cancels).
- **Representation** (not compared): order among exactly tied scores, CSV formatting/precision beyond the stated minimum, internal matrix layout.

## 4. Discriminator variants (measure effects; do not assume failure or equivalence)

Run each through the candidate grader; it must reject each unless measurement shows the deviation is within the correct-implementation floor, in which case the variant is a legitimate equivalent and must not be claimed different:
- tie-corrected variance (scanpy `tie_correct=True`; scipy asymptotic default) — ties are abundant in this zero-inflated matrix, so the tie term is nonzero; expected z shift, magnitude unmeasured;
- continuity correction (`use_continuity=True`) — different z definition;
- per-sample (batch-wise) normalization, or a fixed CP10k/CPM target, instead of the pooled median;
- test on raw (unnormalized) counts — per-cell scaling is not rank-preserving across cells, so z/p/log2fc are expected to change (measure);
- dropping log1p while keeping the per-cell median scaling — z and p are **rank-based and invariant** under a common strictly monotone transform; only the effect-size column changes. The log2fc comparison must catch this; verify it does;
- tested-universe deviations (HVG restriction, per-sample filtering, outer union, summing duplicate-symbol features) — structural key-set mismatch;
- cell-population deviations vs the supplied table (mismatch must also surface as a self-reported error per the brief);
- cluster-vs-single-reference, rest-restricted, per-sample or pseudobulk contrasts — different scientific questions;
- BH pooled across clusters, or Bonferroni instead of BH — different pval_adj;
- min/max instead of average ranks — changes W_c where ties exist;
- p-value via naive `1 − Φ` subtraction — must spuriously zero representable small probabilities; measure how many reference p-values are nonzero but below what naive subtraction can express, and confirm the grader catches it;
- one-sided tests.

## 5. Validation runs required before release

1. Materialize both derived inputs and pass all §1 checks against the staged h5 files and recorded artifacts.
2. Reference stability: re-run `trial/reference.py` on the staged inputs (offline 4 CPU / 8 GiB / 600 s; recorded full-pipeline cost 147.5 s, 5.18 GiB peak child RSS) and confirm the exported tables reproduce (any nondeterminism must be recorded — none is expected in this branch).
3. Clean-room implementation of the public conventions (float64, no scanpy DE call), run within the solver sandbox, and measure per-row deviations vs the recorded reference across **all** rows for score, log2fc, log10 p (nonzero) and pval_adj — the correct-implementation deviation floor. This also proves the DE-only branch fits the solver budget and then output size (reference CSV ≈ 28 MB / ~400k rows fits the 10 GiB disk limit).
4. Run every §4 discriminator through the candidate grader; require rejection; record measured deviations; never widen a tolerance to absorb a discriminator.
5. Public-brief hygiene: confirm the released brief contains no measured counts, label ranges, cluster number, marker gene identities, sample cell counts, or private paths.
6. Only after 1–5: finalize numeric comparison rules, set `semantic_fidelity_validated`, release.

## 6. Open questions

- Reference block group order (numeric ascending?) — resolved by the §2 pre-check; adjust the public sort rule if it differs.
- Whether the h5 files contain non-GEX features (affects only the map's extent, not the solver contract).
- Cross-sample `gene_id` ↔ `ensembl_id` consistency count (provenance only; join remains identifier-based).
- Final p-value rule (log-scale tolerance vs underflow-collapsed equality) and the score/log2fc tolerance values — pending §3/§5 calibration; deliberately unset.
- Whether any exact score ties occur within blocks (affects only the non-increasing-order check; keyed comparison is immune).
