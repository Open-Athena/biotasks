#!/usr/bin/env python3
"""Solve the LuxC profile-HMM task from the supplied inputs only.

Builds a Plan7 profile HMM from the supplied Stockholm alignment with
default HMMER3 model construction, searches the supplied protein FASTA
database with the default HMMER3 hmmsearch pipeline, and writes the two
requested outputs (HMMER3/f ASCII profile and hmmsearch-style domain
table) using the same native writers as the source analysis.
"""
import argparse
import sys
from pathlib import Path


def locate(root: Path, filename: str) -> Path:
    root = Path(root)
    direct = root / "data" / ("msa" if filename.endswith(".sto") else "seqs") / filename
    if direct.is_file():
        return direct
    nested = root / "inputs" / "data" / ("msa" if filename.endswith(".sto") else "seqs") / filename
    if nested.is_file():
        return nested
    for candidate in sorted(root.rglob(filename)):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"ERROR: could not locate {filename} under {root}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args(argv)

    import pyhmmer

    msa_path = locate(args.input_dir, "LuxC.sto")
    faa_path = locate(args.input_dir, "LuxC.faa")

    alphabet = pyhmmer.easel.Alphabet.amino()

    # --- Model construction (default hmmbuild-equivalent configuration) ---
    with pyhmmer.easel.MSAFile(str(msa_path), digital=True, alphabet=alphabet) as msa_file:
        msa = msa_file.read()

    builder = pyhmmer.plan7.Builder(alphabet)
    background = pyhmmer.plan7.Background(alphabet)
    hmm, _, _ = builder.build_msa(msa, background)

    # --- Profile search (default hmmsearch-equivalent pipeline) ---
    pipeline = pyhmmer.plan7.Pipeline(alphabet, background=background)
    with pyhmmer.easel.SequenceFile(str(faa_path), digital=True, alphabet=alphabet) as seq_file:
        hits = pipeline.search_hmm(hmm, seq_file)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "LuxC.hmm", "wb") as output_file:
        hmm.write(output_file)

    with open(out_dir / "LuxC.domtbl", "wb") as output_file:
        hits.write(output_file, format="domains")

    print(f"built HMM: {hmm.name}, M={hmm.M}, search reported {len(hits)} target(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

