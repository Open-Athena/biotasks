import os

os.makedirs("/work/outputs", exist_ok=True)

# Final result: peaks with their strongest motif, blacklist-filtered
df_peaks_maxmotif_clean.to_csv(
    "/work/outputs/peaks_with_strongest_motif_blacklist_filtered.csv",
    index=False,
)

# Distribution of overlapping motif counts per peak (supports the
# "peaks without motifs" finding shown in the histogram and printed fraction)
pd.DataFrame({"motifs_per_peak": motifs_per_peak}).to_csv(
    "/work/outputs/motifs_per_peak.csv",
    index=False,
)