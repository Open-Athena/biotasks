#!/usr/bin/env python3
"""Reference solution for the LuxC profile-HMM task.

Solves the public task using only the supplied inputs:
  1. build a Plan7 profile HMM from the Stockholm alignment with default
     Builder/Background settings, writing HMMER3/f ASCII to LuxC.hmm;
  2. search the FASTA database with the HMM using the default Pipeline
     settings (hmmsearch defaults), writing the --domtblout-format domain
     hit table to LuxC.domtbl.
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    from pyhmmer import easel, plan7

    msa_path = os.path.join(args.input_dir, "data", "msa", "LuxC.sto")
    faa_path = os.path.join(args.input_dir, "data", "seqs", "LuxC.faa")

    alphabet = easel.Alphabet.amino()

    # Task A: build the profile HMM from the curated alignment.
    with easel.MSAFile(msa_path, digital=True, alphabet=alphabet) as msa_file:
        msa = msa_file.read()

    builder = plan7.Builder(alphabet)
    background = plan7.Background(alphabet)
    hmm, _, _ = builder.build_msa(msa, background)

    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "LuxC.hmm"), "wb") as output_file:
        hmm.write(output_file)

    # Task B: search the protein database with the built HMM, hmmsearch defaults.
    pipeline = plan7.Pipeline(alphabet, background=background)
    with easel.SequenceFile(faa_path, digital=True, alphabet=alphabet) as seq_file:
        hits = pipeline.search_hmm(hmm, seq_file)

    with open(os.path.join(args.output_dir, "LuxC.domtbl"), "wb") as output_file:
        hits.write(output_file, format="domains")

    name = hmm.name.decode() if isinstance(hmm.name, bytes) else hmm.name
    print("built HMM %s with %d consensus positions" % (name, hmm.M))
    print("sequences reported: %d" % len(hits))


if __name__ == "__main__":
    main()

