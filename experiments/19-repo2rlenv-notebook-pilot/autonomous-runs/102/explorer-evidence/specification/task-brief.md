# Assign CTCF motifs to ChIP-seq peaks, with blacklist-region filtering

## Objective

From three genomic interval files — CTCF ChIP-seq peaks, a CTCF motif track, and ENCODE blacklist regions — reproduce two results of the motif-to-peak assignment analysis:

1. A table of ChIP-seq peaks, each annotated with the strongest overlapping motif, after conservative removal of peak bases near blacklisted regions.
2. The number of overlapping motifs for each input peak record.

## Inputs (task-relative paths; all gzip-compressed, tab-separated, no header lines, 0-based half-open `[start, end)` coordinates)

- `inputs/ENCFF401MQL.bed.gz` — CTCF ChIP-seq peaks (HFF, ENCODE, GRCh38), narrowPeak: 10 fields per record: `chrom, start, end, name, score, strand, fc, -log10p, -log10q, summitOffset`. `fc` (field 7, the signal value / fold enrichment) is the reported peak strength.
- `inputs/MA0139.1.tsv.gz` — JASPAR MA0139.1 CTCF motif occurrences (hg38, UCSC-track style): 7 fields: `chrom, start, end, name, score, pval, strand`. The motif p-value score is field 6. **The analysis parses this file discarding its first line** (the pipeline's parsing convention), so the motif set consists of the records from the second line onward, in file order.
- `inputs/ENCFF356LFX.bed.gz` — ENCODE blacklist regions, bed3: `chrom, start, end`.

"Peak record order" means the line order of the peaks file; "motif record order" means the line order of the motif file after the skipped first line.

## Methodology (defines the requested quantities)

1. **Overlap convention.** A peak and a motif overlap if and only if they are on the same chromosome (exact label equality; do not rename or canonicalize chromosome labels in any way) and their half-open spans intersect with positive length. Intervals that only share an endpoint do not overlap. Strand is ignored for overlap.
2. **Motifs per peak.** For each input peak record, in input record order, count how many motif records overlap it. This is computed over the full peak set and full motif set, before any blacklist filtering; peaks with no overlapping motif get count 0.
3. **Strongest motif per peak group.** Group the peak–motif overlap results by the peak's coordinates `(chrom, start, end)`: input peak records that share identical coordinates form a single assignment group, and each group yields exactly one annotated peak row. Within a group, the assigned motif is the overlapping motif with the largest motif p-value. When several overlapping motifs tie for the maximum, use the deterministic convention of the pipeline: the pair that appears first when overlapping pairs are scanned in ascending input peak record order and, within one peak record, ascending input motif record order. A group whose peaks have no overlapping motif gets no assigned motif.
4. **Peak-table columns.** For each group, report the peak's `chrom, start, end, fc` and the assigned motif's `chrom_2, start_2, end_2, pval_2, strand_2`. For groups with no assigned motif, all five motif fields are empty and `pval_2` carries the sentinel value `-1` (an empty/missing field is an accepted equivalent encoding of the same "no motif p-value to report" state).
5. **Blacklist filtering.** Expand every blacklist interval by 1000 bp on both sides (`start − 1000`, `end + 1000`). From each annotated peak interval, remove every base covered by any expanded blacklist interval (union coverage; base-level set subtraction, not a distance-from-summit or peak-center criterion). A peak with no surviving bases is dropped entirely. A partially covered peak is split into its maximal surviving sub-intervals, each reported as its own row; every fragment retains the peak's `fc` value and all its assigned-motif fields unchanged, even if the motif itself falls inside a removed portion. (The `motifs_per_peak` output is *not* affected by this filtering.)

## Required outputs

1. `peaks_with_strongest_motif_blacklist_filtered.csv` — comma-separated with exactly one header line, columns in this exact order with these exact names:
   `chrom,start,end,fc,chrom_2,start_2,end_2,pval_2,strand_2`
   - `chrom`: chromosome label of the surviving peak fragment; `start`, `end`: integer fragment boundaries; `fc`: the peak's signal value (decimal).
   - `chrom_2`, `start_2`, `end_2`: the assigned motif's chromosome label and integer coordinates; `pval_2`: its numeric p-value score; `strand_2`: `+` or `-` — all empty (and `pval_2` = −1) for peaks with no assigned motif.
   - Missing values are empty CSV fields. Values must parse to the exact underlying numbers; do not round, rescale or reformat values. Row order is not prescribed.
2. `motifs_per_peak.csv` — comma-separated with exactly one header line, a single column named `motifs_per_peak`: one integer count per input peak record, **in input record order** (the positional correspondence to the peaks file is part of the requested result).

## Environment and limits

Execution is offline; sandbox: 4 CPUs, 8 GiB memory, 10 GiB disk; 600 s time limit. A compatible reference environment (Python 3.13, bioframe 0.8.0, pandas 3.1.0, NumPy 2.5.4) can be supplied for convenience, but any tool chain is acceptable provided the outputs meet the contract above.
