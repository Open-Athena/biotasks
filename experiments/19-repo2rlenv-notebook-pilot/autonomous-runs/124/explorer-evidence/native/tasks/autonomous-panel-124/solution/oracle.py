import argparse
import os


def locate(root, rel):
    """Locate a required input file relative to the given input root."""
    for cand in (os.path.join(root, rel), os.path.join(root, "inputs", rel)):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"required input {rel!r} not found under {root}")


def main():
    parser = argparse.ArgumentParser(description="Build the LuxC profile HMM and search the protein database")
    parser.add_argument("--input-dir", required=True, help="Directory containing the supplied inputs")
    parser.add_argument("--output-dir", required=True, help="Directory to write the required outputs")
    args = parser.parse_args()

    import pyhmmer
    from pyhmmer import easel, plan7

    # Amino-acid alphabet used for reading, building, and searching.
    alphabet = easel.Alphabet.amino()

    # 1. Read the Stockholm alignment as one digital amino-acid MSA.
    msa_path = locate(args.input_dir, "msa/LuxC.sto")
    with easel.MSAFile(msa_path, digital=True, alphabet=alphabet) as msa_file:
        msa = msa_file.read()

    # 2. Build the profile HMM with default HMMER3 construction settings.
    builder = plan7.Builder(alphabet)
    background = plan7.Background(alphabet)
    hmm, _, _ = builder.build_msa(msa, background)

    # Write the profile HMM in HMMER3 ASCII format.
    os.makedirs(args.output_dir, exist_ok=True)
    hmm_path = os.path.join(args.output_dir, "LuxC.hmm")
    with open(hmm_path, "wb") as output_file:
        hmm.write(output_file)

    # 3. Search the protein sequence database with the built HMM,
    #    using hmmsearch defaults (local mode, E<=10 / domE<=10 thresholds,
    #    default MSV/Viterbi/Forward filtering, Z from the sequence count).
    pipeline = plan7.Pipeline(alphabet, background=background)
    seq_path = locate(args.input_dir, "seqs/LuxC.faa")
    with easel.SequenceFile(seq_path, digital=True, alphabet=alphabet) as seq_file:
        hits = pipeline.search_hmm(hmm, seq_file)

    # Write the search hits in hmmsearch domain-table format.
    domtbl_path = os.path.join(args.output_dir, "LuxC.domtbl")
    with open(domtbl_path, "wb") as f:
        hits.write(f, format="domains")


if __name__ == "__main__":
    main()

