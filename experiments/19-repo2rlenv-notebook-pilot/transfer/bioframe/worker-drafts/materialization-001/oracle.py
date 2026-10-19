#!/usr/bin/env python3
"""solve.py -- assign the strongest CTCF motif to every CTCF ChIP-seq peak,
then conservatively trim the peaks around ENCODE blacklisted regions.

Clean-room implementation of the public task: plain gzip text parsing and
explicit interval arithmetic (no bioframe, no pandas). It reads only the
files supplied in --input-dir and writes only into --output-dir.

Inputs (coordinates are 0-based half-open, GRCh38/hg38):
  ENCFF401MQL.bed.gz  CTCF ChIP-seq peaks (HFF), gzipped narrowPeak, no header
  MA0139.1.tsv.gz     JASPAR MA0139.1 motif track, gzipped TSV; its first
                      physical line is a UCSC track declaration (skipped)
  ENCFF356LFX.bed.gz  ENCODE blacklist regions, gzipped BED3
Output:
  ctcf_peaks_maxmotif_clean.csv
"""
import argparse
import csv
import gzip
import heapq
import os

PEAK_FILE = "ENCFF401MQL.bed.gz"
MOTIF_FILE = "MA0139.1.tsv.gz"
BLACKLIST_FILE = "ENCFF356LFX.bed.gz"
OUT_FILE = "ctcf_peaks_maxmotif_clean.csv"
PAD = 1000
MOTIF_NCOLS = 7


def read_lines(path):
    """Yield the non-empty lines of a gzipped text file."""
    with gzip.open(path, "rt", newline="") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")
            if line.strip():
                yield line


def load_peaks(path):
    """Return (chrom, start, end, fc) peak records in file order."""
    peaks = []
    for line in read_lines(path):
        f = line.split("\t")
        if len(f) < 7:
            raise ValueError("peak row with fewer than 7 columns: %r" % line)
        peaks.append((f[0], int(f[1]), int(f[2]), float(f[6])))
    return peaks


def parse_pval(text):
    """Parse a motif pval; empty/NA fields are undefined (None)."""
    text = text.strip()
    if text in ("", ".", "NA", "nan", "NaN", "None"):
        return None
    return float(text)


def load_motifs(path):
    """Return (chrom, start, end, pval, strand) motif records in row order.

    pval is the motif score as -log10(p-value) * 100; it is None when the
    supplied field does not define a score.
    """
    motifs = []
    seen_first_line = False
    for line in read_lines(path):
        f = line.split("\t")
        if not seen_first_line:
            seen_first_line = True
            if len(f) != MOTIF_NCOLS:
                continue  # UCSC track declaration, not a data row
        if len(f) != MOTIF_NCOLS:
            raise ValueError("motif row without exactly 7 columns: %r" % line)
        motifs.append((f[0], int(f[1]), int(f[2]), parse_pval(f[5]), f[6]))
    return motifs


def load_blacklist(path):
    """Return (chrom, start, end) blacklist regions."""
    regions = []
    for line in read_lines(path):
        f = line.split("\t")
        if len(f) < 3:
            raise ValueError("blacklist row with fewer than 3 columns: %r" % line)
        regions.append((f[0], int(f[1]), int(f[2])))
    return regions


def assign_motifs(peaks, motifs):
    """Return {peak interval: assigned motif record} for the peaks that have
    at least one overlapping motif.

    The assigned motif is the overlapping motif with the largest pval; if
    several motifs tie for the largest pval, the earliest one in the motif
    track's row order wins.  Peaks are collapsed to their distinct intervals.
    """
    peaks_by_chrom = {}
    for chrom, start, end, _fc in peaks:
        peaks_by_chrom.setdefault(chrom, set()).add((start, end))

    motifs_by_chrom = {}
    for j, (chrom, start, end, pval, strand) in enumerate(motifs):
        motifs_by_chrom.setdefault(chrom, []).append((start, end, pval, strand, j))

    best = {}  # peak interval -> (-pval, motif row order), minimal wins
    for chrom, pset in peaks_by_chrom.items():
        mlist = motifs_by_chrom.get(chrom)
        if not mlist:
            continue
        groups = sorted(pset)
        msorted = sorted(mlist, key=lambda m: (m[0], m[4]))
        mcursor = 0
        active = []  # min-heap keyed by motif end
        for gstart, gend in groups:
            # admit every motif that starts before this peak ends
            while mcursor < len(msorted) and msorted[mcursor][0] < gend:
                ms, me, mp, mst, mj = msorted[mcursor]
                heapq.heappush(active, (me, ms, mp, mst, mj))
                mcursor += 1
            # evict motifs that end at or before this peak starts
            while active and active[0][0] <= gstart:
                heapq.heappop(active)
            # every remaining active motif shares at least one base with the peak
            for _me, _ms, mp, _mst, mj in active:
                if mp is None:
                    continue  # undefined pval -> cannot be the strongest motif
                cand = (-mp, mj)
                cur = best.get((chrom, gstart, gend))
                if cur is None or cand < cur:
                    best[(chrom, gstart, gend)] = cand
    return {k: motifs[v[1]] for k, v in best.items()}


def merged_expanded_blacklist(regions, pad):
    """Expand each blacklist interval by pad on both sides and merge per chrom.

    Returns {chrom: sorted disjoint half-open intervals}.
    """
    by_chrom = {}
    for chrom, start, end in regions:
        by_chrom.setdefault(chrom, []).append((start - pad, end + pad))
    merged = {}
    for chrom, ivs in by_chrom.items():
        out = []
        for s, e in sorted(ivs):
            if out and s <= out[-1][1]:
                if e > out[-1][1]:
                    out[-1][1] = e
            else:
                out.append([s, e])
        merged[chrom] = [tuple(iv) for iv in out]
    return merged


def trim(start, end, cuts):
    """Subtract the sorted disjoint `cuts` intervals from [start, end)."""
    pieces = []
    cur = start
    for cs, ce in cuts:
        if ce <= cur:
            continue
        if cs <= cur:
            cur = ce
            continue
        if cs >= end:
            break
        pieces.append((cur, cs))
        cur = ce
    if cur < end:
        pieces.append((cur, end))
    return [(s, e) for s, e in pieces if s < e]


def main():
    ap = argparse.ArgumentParser(
        description="Assign the strongest CTCF motif to each peak, then trim "
                    "peaks within +/-1kb of ENCODE blacklist regions.")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()

    peaks = load_peaks(os.path.join(a.input_dir, PEAK_FILE))
    motifs = load_motifs(os.path.join(a.input_dir, MOTIF_FILE))
    blacklist = load_blacklist(os.path.join(a.input_dir, BLACKLIST_FILE))
    cuts = merged_expanded_blacklist(blacklist, PAD)
    assigned = assign_motifs(peaks, motifs)

    # distinct peak intervals in file order; a repeated interval is annotated
    # with the fold change of its first record
    groups = []
    seen = set()
    for chrom, start, end, fc in peaks:
        key = (chrom, start, end)
        if key in seen:
            continue
        seen.add(key)
        groups.append(key + (fc,))

    os.makedirs(a.output_dir, exist_ok=True)
    out_path = os.path.join(a.output_dir, OUT_FILE)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["chrom", "start", "end", "fc",
                    "motif_chrom", "motif_start", "motif_end",
                    "motif_pval", "motif_strand"])
        for chrom, start, end, fc in groups:
            motif = assigned.get((chrom, start, end))
            for s, e in trim(start, end, cuts.get(chrom, [])):
                if motif is None:
                    # no assigned motif: blank motif fields
                    w.writerow([chrom, s, e, fc, "", "", "", "", ""])
                else:
                    w.writerow([chrom, s, e, fc,
                                motif[0], motif[1], motif[2],
                                float(motif[3]), motif[4]])


if __name__ == "__main__":
    main()

