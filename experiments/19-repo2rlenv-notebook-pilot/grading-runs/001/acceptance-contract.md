# Public acceptance contract: scanpy "Preprocessing and clustering" endpoints (two bone-marrow 10x samples)

## What is graded

Your submission is a directory containing exactly the three declared endpoint files. Nothing else is read, and no other file influences grading:

1. `cell_clusters_umap.csv` — per-cell endpoints (deliverable A).
2. `rank_genes_groups_leiden_res_0.50.csv` — per-cluster differentially expressed genes (deliverable B).
3. `rank_genes_groups_params.json` — recorded run parameters of that DE test (deliverable C).

The graded target is the scientific content of these files as produced by the pinned reference workflow (scanpy 1.12.4 recipe documented in the task brief, section 3). Software choice is open, but no claim is made that arbitrary pipelines or unrelated implementations produce acceptable values; where a number is compared, its accepted range is stated explicitly below. Files are compared by parsed scientific content, never by file hashes or byte layout.

## A. `cell_clusters_umap.csv` — per-cell endpoints

**Format:** UTF-8, comma-separated CSV, one header row, no thousands separators, no quoting of values that contain commas if writing with a standard CSV writer, and no BOM. The header must be exactly, in this order:

```
cell_id,sample,leiden,leiden_res_0.02,leiden_res_0.50,leiden_res_2.00,cell_type_lvl1,umap_1,umap_2
```

Each value must be a plain field (no embedded newlines). Numeric fields must be plain decimal numbers (integer, fixed-point or scientific notation); the tokens `nan`, `inf`, `-inf`, `NaN`, `Infinity`, empty strings, `null` and non-numeric strings in numeric columns are rejected. `umap_1`/`umap_2` must be finite.

**Row population and alignment.** One row per cell retained by the reference's permissive filter (the population after `filter_cells(min_genes=100)`; no doublet or cluster removal happens anywhere in the workflow). Row alignment is by exact string identity of `cell_id` in the reference's stored row order; the grader compares the `cell_id` sequence row by row. The accepted `cell_id` values are the unique barcode identifiers the reference assigns in step 1 (anndata's `obs_names_make_unique` suffixing of the 10x barcode strings; cells whose barcode is duplicated across the two samples carry a `-N` suffix). The accepted `sample` values are exactly the reference's `s1d1`/`s1d3` labels.

**Column rules.**
- `cell_id` — mandatory identifier; every row must have a non-empty value, unique within the file.
- `sample` — mandatory categorical assignment; must equal the reference value for the corresponding row (string identity).
- `leiden`, `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00` — mandatory cluster assignments; each is compared with the reference value for the corresponding row using literal string equality. The Leiden label convention (algorithm-generated integer-like shorthand strings) is part of the target: cluster relabeling, renumbering, reordering of label values or any other transformation of the label set is **not** accepted, because the DE groups, the lineage map and the cross-file label identities are keyed to these exact strings.
- `cell_type_lvl1` — the manual broad-lineage annotation; compared with literal string equality where present, including blank values exactly where the reference is blank. The step-11 mapping of the coarsest solution is a source constant; if the coarsest clustering yields a label outside the map, the corresponding cells are left blank — do not invent labels.
- `umap_1`, `umap_2` — the two UMAP coordinates, compared per axis with the reference value per cell. **Numeric rule:** the submission coordinate must lie within half an IEEE-754 binary32 unit-in-the-last-place of the reference coordinate, i.e. it must round (round-to-nearest, ties-to-even) to the same binary32 number as the reference value. Rationale: the reference workflow stores these coordinates as binary32, so the exported digits carry exactly binary32 information; a serialization/parse jitter smaller than half a stored unit cannot be meaningful at this precision, while any larger deviation is a computational deviation of the embedding. Axis correspondence is fixed (`umap_1` to `umap_1`); no axis swap, sign flip, rotation, scaling or translation is accepted, because the reference embedding's orientation is defined by the pinned workflow and every downstream interpretation (plots, cluster adjacency) depends on it.

## B. `rank_genes_groups_leiden_res_0.50.csv` — per-cluster DE endpoints

**Format:** UTF-8 CSV, one header row, exactly:

```
group,names,scores,pvals_adj,pvals,logfoldchanges
```

Numeric columns must be plain finite decimal numbers as in file A.

**Row population.** One row per (cluster of the `leiden_res_0.50` solution, gene) — the full leaderboard ranks every analyzed gene within every cluster, so the number of rows equals the number of 0.50-resolution clusters multiplied by the number of genes retained after the reference's filtering. Rows of the same cluster are consecutive, in the reference's stored group order, and within each group in the stored rank order (descending `scores`). The grader compares group-block order, per-group row counts and within-block rank positions against the reference.

**Column rules.**
- `group` — the cluster label; the set of `group` values must equal the set of labels appearing in the `leiden_res_0.50` column of file A (label-set identity only; the two files have different row units — per-group gene rows here, per-cell rows there — and neither set of per-group counts is interchangeable). Group labels are compared literally — the same convention as file A.
- `names` — the gene identifier; the set of genes ranked within each group must equal the reference gene set for that group (`var_names` after the reference's step-1 make-unique processing).
- `scores` — the Wilcoxon rank-sum statistic. **Numeric rule:** the submission value must lie within half a binary32 unit-in-the-last-place of the reference value at the same (group, rank position). The reference stores this statistic as binary32; this is the exact information the exported table carries.
- `pvals_adj`, `pvals` — Benjamini–Hochberg adjusted and raw p-values; compared **exactly** as parsed double-precision numbers, including all digits of very small values. Exact zeros must be preserved exactly: values that underflowed to zero in the reference must be submitted as zero (a nonzero submission where the reference is zero, or vice versa, is a failure). Zero is a meaningful value here and is checked as such. Values must lie in [0, 1].
- `logfoldchanges` — log2 fold change; same binary32-precision rule as `scores`.

**Permitted variation — rank ties.** Within a group, rows may be permuted **only** among rows whose `scores`, `pvals` and `pvals_adj` are all identical (the reference's tie structure); such rows are indistinguishable in the exported statistics. Any permutation that moves a gene across a difference in `scores`, `pvals` or `pvals_adj` is rejected. There is no permitted variation in the group set, group order, per-group gene universe or per-(group, gene) statistics.

## C. `rank_genes_groups_params.json` — DE run parameters

**Format:** a single JSON object mapping (UTF-8, no NaN/Infinity constants, scalar values only). The submission must record exactly the same set of parameter keys as the reference, each with an equal value of the same JSON type (e.g. `use_raw` as boolean `false`, `layer` as `null`). Missing keys, unexpected keys, wrong types or changed values fail. JSON key order and whitespace do not matter.

## Cross-file consistency

- The `group` label set of file B must equal the `leiden_res_0.50` label set of file A (literal string identity; the labels are the same clustering).
- File C must describe the DE test that produced file B.
- File A must contain one row per retained cell and file B one row per (cluster, gene) — these are different row units and are not compared to each other by count.

## Consequences of the literal-label rule

Relabeling clusters (e.g. renaming "0" to "A", renumbering, or permuting label sets) is not an accepted variation: the reference's `cell_type_lvl1` mapping is a literal constant over the coarsest labels, the DE groups are keyed to the 0.50-resolution labels, and the exported tables' row order and cross-file label identities depend on them. A submission whose labels differ from the reference's will fail the corresponding cluster, annotation, DE group and cross-file checks. Similarly, embedding orientation changes (axis sign flips, rotations) are not accepted, and no label-remapping or coordinate-transformation equivalence is offered.

## Evaluation and failure behavior

All checks listed in the table below are run for every submission. A submission passes only if every check passes. Missing files, malformed files, unreadable files, wrong headers, wrong field counts, duplicated or missing identifiers, blank mandatory values, non-numeric or non-finite numeric values, out-of-range p-values and truncated leaderboards are failed checks, not crashes; the grader reports a failing message for each affected check, writes a valid JSON report, and exits 0. Values are never read from probe names, paths, timestamps or environment variables.
