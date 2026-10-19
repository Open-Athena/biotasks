# Preparation worker output

Rendered from [plan.json](plan.json). Generated commands and source edits have not been executed. Only structural checks have run; scientific fidelity is unreviewed.

## Decision

prepare

The notebook's terminal scientific product, stated in its own narrative ('there it is! we now have a dataframe containing positions of CTCF ChIP peaks, including the strongest motif underlying that peak, and after conservative filtering for proximity to blacklisted regions'), is df_peaks_maxmotif_clean. The appended code only creates /work/outputs and writes that existing dataframe to CSV with its final columns and row order unchanged; no recomputation, filtering or analysis is added. Every remaining column is an endpoint field (peak coordinates and fold change, strongest motif coordinates, p-value and strand), so the table is exported whole; the pandas index is dropped because rows are identified by peak/motif coordinates and the index carries no narrative meaning. All plots and printed diagnostics are left untouched.

## Artifact: ctcf_peaks_maxmotif_clean.csv

Final table of CTCF ChIP-seq peaks, each with its strongest overlapping JASPAR CTCF motif (motif coordinates, -log10 p-value x100, strand) and the peak's fold change, after removal of peaks within 1 kb of expanded ENCODE blacklist regions; rows identified by peak and motif coordinates.

Source evidence: The notebook's stated goal is 'one way to assign CTCF motifs to CTCF ChIP-seq peaks', and the closing narrative declares the end product: 'there it is! we now have a dataframe containing positions of CTCF ChIP peaks, including the strongest motif underlying that peak, and after conservative filtering for proximity to blacklisted regions'. The corresponding existing variable df_peaks_maxmotif_clean is produced in the original script by df_peaks_maxmotif_clean = bioframe.subtract(df_peaks_maxmotif, bioframe.expand(blacklist, 1000)), where df_peaks_maxmotif holds the per-peak strongest motif selected via idxmax over overlap p-values; the script ends by displaying df_peaks_maxmotif_clean.iloc[7:15]. The variable is intact at completion.

## Worker-returned export code

```python
# --- Endpoint export: terminal scientific results ---

import os

os.makedirs("/work/outputs", exist_ok=True)

# Final result of the tutorial: CTCF ChIP-seq peaks (HFF, ENCODE ENCFF401MQL)
# each assigned the strongest overlapping JASPAR CTCF motif (MA0139.1), with
# peaks within +/-1kb of ENCODE blacklist regions (ENCFF356LFX) removed.
# Written as-is from the dataframe produced by bioframe.subtract above.
df_peaks_maxmotif_clean.to_csv(
    "/work/outputs/ctcf_peaks_maxmotif_clean.csv", index=False
)
```

## Controller-assembled reference script

[reference.py](reference.py): untouched original script followed by the export code above.

## Controller-computed diff

```diff
--- baseline.py
+++ reference.py
@@ -161,3 +161,18 @@
 # filtering for proximity to blacklisted regions
 
 df_peaks_maxmotif_clean.iloc[7:15]
+
+
+# --- Endpoint export: terminal scientific results ---
+
+import os
+
+os.makedirs("/work/outputs", exist_ok=True)
+
+# Final result of the tutorial: CTCF ChIP-seq peaks (HFF, ENCODE ENCFF401MQL)
+# each assigned the strongest overlapping JASPAR CTCF motif (MA0139.1), with
+# peaks within +/-1kb of ENCODE blacklist regions (ENCFF356LFX) removed.
+# Written as-is from the dataframe produced by bioframe.subtract above.
+df_peaks_maxmotif_clean.to_csv(
+    "/work/outputs/ctcf_peaks_maxmotif_clean.csv", index=False
+)
```

## Excluded outputs

- Motifs-per-peak distribution and 'fraction of peaks without motifs' (motifs_per_peak, plt.hist, printed fraction): a diagnostic characterizing overlap multiplicity and unannotated peaks that motivates the strongest-motif assignment step, not an independent endpoint; the stored count array also carries no peak identifiers.

- Peak strength vs motif strength relationship (scatter and correlation): the correlation coefficient is computed only inside the plt.title call, so these plot-only values cannot be exported without adding computation.

- Reverse-question branch ('how many motifs overlap a ChIP-seq peak?'): its interpreted result, the cumulative probability curve versus motif p-value, is computed entirely inside plt.plot from the sorted table m; the underlying df_motifs_peaks table is an intermediate feeding that plot rather than the interpreted result.

- Distance of peaks to blacklist regions (closest_to_blacklist histogram): a diagnostic supporting the decision to filter +/-1kb around blacklisted regions; also displayed only as a histogram.

- df_peaks_maxmotif in its pre-blacklist-filter state: an intermediate toward df_peaks_maxmotif_clean; the variable is subsequently overwritten by column selection/rename, so the earlier full-column version is no longer recoverable and was not an endpoint in itself.

## Unresolved assumptions

- The final column set/order of df_peaks_maxmotif_clean is assumed to be chrom, start, end, fc, chrom_2, start_2, end_2, pval_2, strand_2 after the rename and subtract steps; confirm at execution.

- Peaks with no overlapping motif retain NaN in pval_2 and empty motif coordinates; in CSV these appear as empty fields.

- The inplace replace/rename chained-assignment patterns in the original script may warn or behave differently under the execution environment's pandas version; fidelity of the final-state table is a validation question, not something the export changes.

- Remote retrieval of the ENCODE peaks, ENCODE blacklist and JASPAR motif files must succeed during the network-enabled setup stage; the offline reference run assumes those inputs are staged unchanged.
