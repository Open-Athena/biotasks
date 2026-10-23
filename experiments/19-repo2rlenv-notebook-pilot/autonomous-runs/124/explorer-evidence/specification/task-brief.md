## Objective

Build a profile HMM from a protein multiple sequence alignment and search a protein sequence database with it, reporting results in HMMER3 standard tabular formats.

## Supplied inputs

- `/inputs/msa/LuxC.sto` — a Stockholm-format multiple sequence alignment of the LuxC acyl-CoA reductase protein family (13 protein sequences, 400 alignment columns). The alignment header carries family annotation (ID/name `LuxC`, accession, description, gathering/trusted/noise cutoffs — CB `#=GF GA`, `#=GF TC`, `#=GF NC`).
- `/inputs/seqs/LuxC.faa` — a FASTA file of protein sequences (the sequence database to search).

## Methodology

1. **Read** the Stockholm alignment in the amino-acid alphabet (one MSA, all sequences).
2. **Build a profile HMM** from the alignment using standard HMMER3 profile-HMM construction with default settings: relative sequence weighting (Henikoff position-based), effective sequence number by relative-entropy targeting, mixture Dirichlet priors for amino acids, default position archiving thresholds, and E-value calibration of the MSV/Viterbi/Forward score statistics to a standard amino-acid background distribution. The model name must come from the alignment name; the GA/TC/NC cutoff annotations embedded in the alignment must be carried through to the model.
3. **Search** the protein database with the built profile HMM using the standard HMMER `hmmsearch`-equivalent settings: local alignment mode, per-hit reporting threshold E ≤ 10, per-domain reporting threshold E ≤ 10, default filtering (MSV/Viterbi/Forward as in hmmsearch defaults), E-values computed with the actual number of sequences searched. Report the resulting sequence and domain hits.
4. Use the same standard amino-acid background model for both building and searching.

You may use any software that implements HMMER3 profile construction and search (e.g., pyhmmer, HMMER3 binaries, or a compatible work-alike). No network access is available. Basic environment (CPU-only, ≤ 8 GB RAM, minutes of runtime at most) is provided; the reference runtime is well under one second on this data.

## Required outputs

**1. `/outputs/LuxC.hmm` — the built profile HMM**, in HMMER3 ASCII text format (dedicated `HMM` line as in HMMER3/f), containing the model name derived from the alignment, the alignment accession, model length, calibration statistics (MSV/Viterbi/Forward local-mode parameters), the GA/TC/NC cutoff scores carried from the alignment, and all per-position emission and transition parameters for the 400 model positions.

Write all model content per the HMMER3 `hmmbuild`/`hmmconvert` style of output. Run-specific transient fields (the `DATE` build timestamp and the `COM` command line) are not graded, as they vary per run.

**2. `/outputs/LuxC.domtbl` — the search results**, in HMMER `hmmsearch` domain-table format, with data-free comment lines (`#`) followed by exactly one row per reported domain. Each row must contain: target sequence name and accession, target length, query (HMM) name and accession, query length, full-sequence E-value/score/bias, per-domain E-values/score/bias, domain number, model coordinates (from/to), alignment coordinates (from/to), envelope coordinates (from/to), average posterior accuracy, and target description. Rows must be ordered as in the hmmsearch domain table (by full-sequence E-value, best first, then tlen/name ordering per the hmmsearch convention).

The result set (which target sequences yield reported domains, how many domains per sequence, and their coordinates) is part of the requested scientific content, not just the formatting.

## Notes on expected difficulty

- The alignment is small (13 sequences, 400 columns) and the database small, so the search always completes. However, the E-value and bit-score values are sensitive to exact calibration of profile statistics; produce them with your chosen tool's standard default calibration, not ad-hoc scaling.
- Scientific E-value thresholds filter the reported set: not every sequence in `/inputs/seqs/LuxC.faa` necessarily appears in the output — only those with reported domains under the stated thresholds. Do not pad or prune rows heuristically; let the methodology decide.
