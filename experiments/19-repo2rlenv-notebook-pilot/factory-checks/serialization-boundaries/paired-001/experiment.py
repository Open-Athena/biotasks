#!/usr/bin/env python3
"""Diagnostic harness: does saving the profile HMM to its task-requested
HMMER3/f ASCII artifact and reloading it change the downstream hmmsearch
results?

Two branches, identical in every respect (inputs, methods, defaults, seed,
output formats) except a single hand-off boundary:

  direct : build the HMM -> write the HMMER3/f artifact -> search with the
           in-memory HMM object (exactly the reference computation).
  stored : build the SAME HMM -> write the SAME artifact bytes -> reload the
           artifact from disk with HMMFile -> search with the reloaded HMM.

The only difference is the ASCII round-trip (serialization to 5-decimal
negative-log probabilities, `*` for zero) through the task's requested
artifact format before the search.

Usage:
    harness.py --input-dir INPUT_DIR --output-dir OUTPUT_DIR

Writes:
    OUTPUT_DIR/direct/LuxC.hmm,  OUTPUT_DIR/direct/LuxC.domtbl
    OUTPUT_DIR/stored/LuxC.hmm, OUTPUT_DIR/stored/LuxC.domtbl
"""
import argparse
import io
import os


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args(argv)

    import pyhmmer
    from pyhmmer import easel, plan7

    msa_path = os.path.join(args.input_dir, "data", "msa", "LuxC.sto")
    seq_path = os.path.join(args.input_dir, "data", "seqs", "LuxC.faa")

    # ------------------------------------------------------------------
    # Common build: executed ONCE so both branches start from exactly the
    # same object and the same calibration RNG stream (Builder defaults,
    # seed 42), eliminating any per-branch build/RNG divergence.
    # ------------------------------------------------------------------
    alphabet = easel.Alphabet.amino()

    with easel.MSAFile(msa_path, digital=True, alphabet=alphabet) as msa_file:
        msa = msa_file.read()

    builder = plan7.Builder(alphabet)  # HMMER 3 defaults, calibration seed 42
    build_background = plan7.Background(alphabet)
    hmm, _, _ = builder.build_msa(msa, build_background)

    # Serialize the calibrated model once, in the task-requested HMMER3/f
    # ASCII format. Both branches later write these exact bytes as their
    # LuxC.hmm, so the artifact is byte-identical in both branches and no
    # in-memory mutation during a search can leak across branches.
    buf = io.BytesIO()
    hmm.write(buf)
    hmm_bytes = buf.getvalue()

    # ==================================================================
    # Branch 1: DIRECT (reference computation)
    #   HMM artifact is written for the required output, but the search
    #   uses the in-memory model (no round-trip).
    # ==================================================================
    direct_dir = os.path.join(args.output_dir, "direct")
    os.makedirs(direct_dir, exist_ok=True)
    with open(os.path.join(direct_dir, "LuxC.hmm"), "wb") as f:
        f.write(hmm_bytes)

    pipeline_direct = plan7.Pipeline(
        alphabet, background=plan7.Background(alphabet)
    )
    with easel.SequenceFile(seq_path, digital=True, alphabet=alphabet) as sf:
        hits_direct = pipeline_direct.search_hmm(hmm, sf)

    with open(os.path.join(direct_dir, "LuxC.domtbl"), "wb") as f:
        hits_direct.write(f, format="domains")

    # ==================================================================
    # Branch 2: STORED (single changed hand-off)
    #   The same intermediate artifact (the task's own requested HMMER3/f
    #   model file) is saved and then RELOADED from disk via HMMFile before
    #   the downstream hmmsearch pipeline runs on it.
    #   NOTE: the in-memory `hmm` object is deliberately NOT used here, so
    #   any mutation the direct branch's search could have made to it
    #   cannot confound this branch; the stored branch operates purely on
    #   the serialized artifact.
    # ==================================================================
    stored_dir = os.path.join(args.output_dir, "stored")
    os.makedirs(stored_dir, exist_ok=True)
    stored_hmm_path = os.path.join(stored_dir, "LuxC.hmm")
    with open(stored_hmm_path, "wb") as f:
        f.write(hmm_bytes)

    with plan7.HMMFile(stored_hmm_path) as hmm_file:
        hmm_reloaded = hmm_file.read()

    pipeline_stored = plan7.Pipeline(
        alphabet, background=plan7.Background(alphabet)
    )
    with easel.SequenceFile(seq_path, digital=True, alphabet=alphabet) as sf:
        hits_stored = pipeline_stored.search_hmm(hmm_reloaded, sf)

    with open(os.path.join(stored_dir, "LuxC.domtbl"), "wb") as f:
        hits_stored.write(f, format="domains")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
