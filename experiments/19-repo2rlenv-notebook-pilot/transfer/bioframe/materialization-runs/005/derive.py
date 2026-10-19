#!/usr/bin/env python3
"""Stage the read-only solver inputs and project the reference answer table.

This performs no scientific computation:
  * the three original input files (ENCODE CTCF peaks for HFF, JASPAR MA0139.1
    motif track, ENCODE blacklist) are copied byte-for-byte into
    <destination>/inputs/,
  * the terminal reference export is copied into <destination>/reference/
    with only its motif columns renamed to the public output schema
    (chrom_2 -> motif_chrom, start_2 -> motif_start, end_2 -> motif_end,
    pval_2 -> motif_pval, strand_2 -> motif_strand); every value and every
    row is passed through unchanged.
"""
import argparse
import hashlib
import json
import os
import shutil

INPUT_BASENAMES = (
    "ENCFF401MQL.bed.gz",
    "MA0139.1.tsv.gz",
    "ENCFF356LFX.bed.gz",
)
REF_FILE = "ctcf_peaks_maxmotif_clean.csv"

ORIGINAL_HEADER = [
    "chrom", "start", "end", "fc",
    "chrom_2", "start_2", "end_2", "pval_2", "strand_2",
]
PUBLIC_HEADER = [
    "chrom", "start", "end", "fc",
    "motif_chrom", "motif_start", "motif_end", "motif_pval", "motif_strand",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_inputs(manifest_path, inputs_dir):
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    entries = {os.path.basename(e["local_path"]): e for e in manifest.get("files", [])}
    copied = []
    for name in INPUT_BASENAMES:
        entry = entries.get(name)
        if entry is None:
            raise SystemExit(f"input {name} missing from source manifest")
        src = entry["local_path"]
        if not os.path.exists(src):
            raise SystemExit(f"input {name} not found at {src}")
        digest = sha256(src)
        if digest != entry["sha256"]:
            raise SystemExit(f"input {name} hash mismatch: {digest} != {entry['sha256']}")
        dst = os.path.join(inputs_dir, name)
        shutil.copyfile(src, dst)
        if sha256(dst) != digest:
            raise SystemExit(f"copy of {name} is not byte-identical")
        copied.append((name, digest))
    return copied


def project_reference(reference_dir, reference_out):
    src = os.path.join(reference_dir, REF_FILE)
    if not os.path.exists(src):
        raise SystemExit(f"reference export not found at {src}")
    lines_read = 0
    with open(src, "r", encoding="utf-8", newline="") as fin, \
            open(reference_out, "w", encoding="utf-8", newline="") as fout:
        for lineno, line in enumerate(fin):
            if lineno == 0:
                fields = line.rstrip("\r\n").split(",")
                if fields != ORIGINAL_HEADER:
                    raise SystemExit(f"unexpected reference header: {fields!r}")
                fout.write(",".join(PUBLIC_HEADER) + "\n")
            else:
                fout.write(line)
            lines_read += 1
    if lines_read < 2:
        raise SystemExit("reference export has no data rows")
    return lines_read - 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-inputs", required=True,
                    help="JSON manifest of the original input files")
    ap.add_argument("--reference-dir", required=True,
                    help="directory holding the original terminal artifacts")
    ap.add_argument("--destination", required=True)
    args = ap.parse_args()

    inputs_dir = os.path.join(args.destination, "inputs")
    reference_dir = os.path.join(args.destination, "reference")
    os.makedirs(inputs_dir, exist_ok=True)
    os.makedirs(reference_dir, exist_ok=True)

    staged = stage_inputs(args.source_inputs, inputs_dir)
    rows = project_reference(args.reference_dir,
                             os.path.join(reference_dir, REF_FILE))
    for name, digest in staged:
        print(f"staged inputs/{name} sha256={digest}")
    print(f"projected reference/{REF_FILE}: {rows} data rows, columns renamed "
          f"to the public schema")


if __name__ == "__main__":
    main()

