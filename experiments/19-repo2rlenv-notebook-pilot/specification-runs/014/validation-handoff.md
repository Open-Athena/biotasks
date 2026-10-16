## 1. Input materialization (proposed — NOT yet built or validated)

**Source**: reference artifact `cell_clusters_umap.csv` (sha256 6f2fc91d14c144f7b7ffc852766318d1dec0acc0312a2e28c08007ce488d7d4d), columns cell_id, sample, leiden, leiden_res_0.02, leiden_res_0.50, leiden_res_2.00, cell_type_lvl1, umap_1, umap_2.

**Derived input** `inputs/cell_groups.csv`:
- Rename `leiden_res_0.50` → `cluster`; keep `sample` verbatim (s1d1/s1d3).
- Recover the raw 10x barcode from `cell_id`: the reference `cell_id` is the 10x barcode with a single `-1` appended by `obs_names_make_unique` for barcodes present in **both** samples (a barcode occurs at most once per sample; `anndata/utils.py:226-249` semantics). Rule: strip one trailing `-1` from `cell_id`s ending in `-1-1`; leave others unchanged.
- Materialization validations (run before release): (a) every produced (`sample`, `barcode`) pair unique; (b) each `barcode` present in that sample's h5 barcode list; (c) row count unchanged (17,041) and per-cluster counts identical to the source column; (d) no column other than sample/barcode/cluster survives.
- **Fallback** if (a)/(b) fails (barcode-format assumption wrong): ship `cell_id` verbatim plus `sample`, and require solvers to reproduce the library's uniquify convention — would need a one-line brief correction.
- Withhold `umap_1/2`, `leiden`, `leiden_res_0.02`, `leiden_res_2.00`, `cell_type_lvl1`. The file contains no DE/marker answers (cluster labels/sizes are the authorized supplied grouping, explicitly not ground truth).
- Pin and record the h5 (sha256 322c30a7…, ca40b287…; provider md5s already verified by staging) and the derived file's sha256.

## 2. Reference for grading (private)

`rank_genes_groups_leiden_res_0.50.csv` (sha256 33aae2d3…; 398,259 rows = 17 group blocks × 23,427 genes, block order = group order, rows within block = descending score). Top-50 per group = first 50 rows of each block. `rank_genes_groups_params.json` confirms reference=rest / wilcoxon / use_raw=false / BH.

## 3. Proposed comparison rules (calibrate before finalizing)

- **Structural**: files present; exact headers; exactly 50 rows per cluster; cluster set = supplied labels; `rank` 1..50 strictly ascending score; no missing/nonfinite values; gene identifiers exactly the reference suffixed identifiers.
- **Identity**: per-cluster top-50 gene sets equal (set equality; multiplicity 1 by construction). Cross-check one shared cluster↔cells mapping across `marker_genes.csv` and `group_sizes.csv`.
- **Numeric (proposals)**: `score`, `log2fc`: |Δ| ≤ max(1e-3, 1e-3·|ref|) — reference values are float32-rounded; two correct float64 implementations should agree far below this. `pval`, `pval_adj`: equal if both ≤ 1e-300 (both-underflow); else |log10 p − log10 p′| ≤ 1e-3. `analysis_summary`: n_cells/n_tested_genes/n_groups exact; `target_sum` within 1e-6 (may be a half-integer median).
- **Calibration to run**: (i) implement the test independently (scipy `rankdata`/`mannwhitneyu(asymptotic, use_continuity=False)` + statsmodels `multipletests(fdr_bh)`) on the staged inputs and measure worst-case deviation from the recorded reference table across all group×gene rows; set each tolerance ≥ measured deviation × 10 safety factor; (ii) verify no boundary tie at rank 50/51 for every group (compare 50th vs 51st scores in each reference block); if ties exist, either extend the cutoff to include all genes tied with the 50th score or lower/raise k; (iii) confirm underflow populations (how many top-50 p-values are exactly 0) and that the both-underflow rule covers them without masking real differences at moderate p.

## 4. Different scientific results that must FAIL (never absorbed by tolerance)

- tie-corrected Wilcoxon (`tie_correct=True`) — scores shift by the tie factor on this heavily tied (zero-inflated) matrix;
- continuity correction (`use_continuity=True`) — z shifts ~1/σ;
- per-sample (batch-wise) normalization or CP10k (T = 10^4) instead of the pooled median — different values, ranks, and log2fc;
- ranks/statistics computed on raw counts or on non-log data;
- DE restricted to highly-variable genes — smaller tested universe, wrong `n_tested_genes`, wrong BH universe and `pvals_adj`;
- cluster-vs-reference-cluster or "rest = other listed groups" semantics; per-sample DE; pseudobulk;
- BH pooled across clusters instead of within-cluster;
- deduplicating gene symbols (summing duplicate-symbol features) or outer-join gene universe — identifier/universe mismatch caught by `n_tested_genes` and gene-set comparison;
- filtering per sample instead of pooled, or non-strict "detected" thresholds.

## 5. Validation runs needed before solver release

1. Build `cell_groups.csv` and pass the materialization checks of §1 (including the h5 barcode cross-check).
2. Run the independent implementation of §3(i) end-to-end offline within the sandbox (4 cores / 8 GiB / 600 s) to confirm the DE branch alone fits the solver budget — reference full pipeline was 147.5 s / ≈5.2 GiB, but the DE-only cost is unmeasured.
3. Run the discriminator variants of §4 through the proposed grader and confirm each is rejected (this is the executable check that tolerances are not masking scientific differences).
4. Confirm the solver-visible brief contains none of: 17,041 / 17,125 / 8,785 / 8,340 / 36,601 / 23,427 / 17 clusters / label range / marker gene names.
5. Re-verify `semantic_fidelity_validated` can be set: currently false; one recorded passing run and a structural audit exist, and repeatability of the recorded run has been observed once only — at minimum confirm the reference DE table is reproducible re-run on the staged inputs before freezing tolerances.

## 6. Unresolved choices (explicitly open)

- Join-key form: raw `barcode` (preferred) vs reference `cell_id` convention — contingent on §1 validation.
- k = 50 for the marker projection (alternatives: 20; the notebook itself reads top-5); boundary-tie handling pending check 3(ii).
- Final p-value comparison rule (log-scale tolerance vs underflow-collapsed equality) and the exact score/log2fc tolerances are proposals until calibration.
- `rank_seed`-style determinism is not an issue (no randomness in the retained branch), but solvers may still use randomized approximate neighbor code in normalization-free steps; enforcement is via output stability, not prescribed seeds.
