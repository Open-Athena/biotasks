# Build a profile HMM for the LuxC acyl-CoA reductase family and search a protein sequence database

## Objective

Build a profile HMM from a multiple sequence alignment of the LuxC acyl-CoA reductase protein family, then use that HMM to search a protein sequence database. Deliver the built profile HMM and the search results in standard HMMER3 output formats.

## Inputs (under `inputs/`)

- `inputs/msa/LuxC.sto` — Stockholm-format multiple sequence alignment of the LuxC acyl-CoA reductase family (13 protein sequences, 400 alignment columns). The alignment header carries family annotation: the alignment name, accession, description, and the GA (gathering), TC (trusted) and NC (noise) cutoff score lines.
- `inputs/seqs/LuxC.faa` — FASTA file of protein sequences; the sequence database to search.

## Method

1. Read the Stockholm alignment as a single amino-acid multiple sequence alignment (all 13 sequences).
2. Build the profile HMM from the alignment using standard HMMER3 profile construction with default `hmmbuild` settings: relative sequence weighting by the Henikoff position-based scheme, effective sequence number by relative-entropy targeting, amino-acid mixture Dirichlet priors, default position-architecting thresholds, and E-value calibration of the MSV/Viterbi/Forward score statistics against the standard amino-acid background distribution. The model must be named after the alignment name recorded in the file, must carry the alignment accession, and must carry the alignment's GA/TC/NC cutoff annotations through unchanged.
3. Search the protein database with this HMM using standard `hmmsearch` default settings: local alignment mode, per-sequence (hit) reporting threshold E ≤ 10, per-domain reporting threshold E ≤ 10, the default MSV/Viterbi/Forward pipeline filtering, and E-values computed from the actual number of sequences searched.
4. Use the same standard amino-acid background frequencies for both building and searching.

Any software implementing HMMER3 profile construction and search may be used (e.g., the HMMER3 binaries, pyhmmer, or a compatible work-alike). No network access is available. Resources: CPU-only, at most 8 GB RAM; the computation is small and completes in minutes at most (the reference run takes well under one second on this data).

## Required outputs (under `outputs/`)

**1. `outputs/LuxC.hmm`** — the profile HMM in HMMER3 ASCII text format: a header containing the model name derived from the alignment name, the alignment accession, the model length (400 match positions), sequence count and effective sequence number, the HMM checksum, the GA/TC/NC cutoff scores carried from the alignment, and the local-mode calibration statistics lines (MSV/VITERBI/FORWARD parameters), followed by the per-position emission, insert and transition parameters for all 400 model positions, terminated with `//`. The DATE build-timestamp line and the COM command-line line are run-specific and may differ between runs; all other content is fixed scientific content.

**2. `outputs/LuxC.domtbl`** — the search results in HMMER `hmmsearch` domain-table format (`--domtblout` style): leading comment lines beginning with `#`, then exactly one row per reported domain with the standard column order: target name, target accession, target length, query (HMM) name, query accession, query length, full-sequence E-value, full-sequence score, full-sequence bias, domain number (and total), conditional and independent per-domain E-values, per-domain score and bias, HMM coordinates (from/to), alignment coordinates (from/to), envelope coordinates (from/to), average posterior accuracy, and target description. Rows must follow the hmmsearch domain-table ordering convention (best full-sequence E-value first, with the hmmsearch tie-break rules). Only domains passing the stated reporting thresholds appear; the set of reported target sequences, the number of domains per sequence, and their coordinates are part of the requested scientific content — do not pad or prune rows heuristically, let the thresholds decide.

Cross-file consistency: the query name, accession and length reported in the domain table must match the model written to `outputs/LuxC.hmm`.

## Acceptance rules

# Acceptance rules (addendum to the task question)

## Compared artifacts
Exactly two files are graded, read from the solver's output root at the declared paths: `LuxC.hmm` (HMMER3 plan7 ASCII profile HMM) and `LuxC.domtbl` (hmmsearch domain table). Each file must be present at its declared path; a file placed under an extra `outputs/` subdirectory inside the output root is at the wrong path and is treated as missing. Values are compared against the reference outputs.

## LuxC.hmm (HMMER3 ASCII profile)
- **Ignored (run-specific):** the `HMMER3/f` version banner line, the `DATE` build-timestamp line and the `COM` command-line line. These lines are excluded from every comparison; the grader does not compare the HMMER version string.
- **Compared exactly:** the model name (`NAME`, from the alignment `#=GF ID`), accession (`ACC`), description (`DESC`), model length (`LENG`, 400 match positions), sequence count (`NSEQ`), HMM checksum (`CKSUM`, integer), and the `GA`/`TC`/`NC` cutoff score pairs (values parsed as real numbers; these are the alignment's cutoff lines carried through unchanged). The presence of `ALPH`, `RF`, `MM`, `CONS`, `CS`, `MAP`, `EFFN`, `NSEQ` and the three `STATS LOCAL` calibration lines is required, as is the trailing `//` terminator.
- **Compared numerically:** `EFFN` (effective sequence number), the `STATS LOCAL MSV`, `STATS LOCAL VITERBI` and `STATS LOCAL FORWARD` parameters, the `COMPO` background line, and every per-position match emission, insert emission and transition row for all 400 model positions in position order. Each of these values is compared with an absolute tolerance of 2×10⁻⁵ (all reference values are indistinguishable beyond their 5-decimal print width); `*` (zero probability) and the `m->m`-style header tokens and consensus/MAP characters are compared as exact text. Trailing whitespace and column alignment is not compared.
- **Structural requirement:** the file must parse as an amino-acid plan7 HMM with a HMMER3 plan7 ASCII reader, declare a model length equal to the number of per-position parameter blocks, and terminate with `//`.

## LuxC.domtbl (hmmsearch domain table)
- Comment lines beginning with `#` are ignored as header text; their presence or exact wording is not compared.
- Every data row is parsed into the standard 22 fixed columns plus the free-text description; a row with fewer than 22 fields fails. Rows are compared **in file order**, which is the hmmsearch ordering: best full-sequence E-value first, with the hmmsearch tie-break rules (in this reference there are no E-value ties, so the ranking is unambiguous).
- **Row count:** the number of reported domain rows is compared exactly — the set of reported targets, the number of domains per target (columns "dom" and "of") and the total row count are requested scientific content. Padding with extra rows or pruning rows is a wrong answer.
- **Exact integer fields:** target length (`tlen`), query length (`qlen`), domain index/total (`#`, `of`), and all HMM, alignment and envelope coordinates (`hmm from/to`, `ali from/to`, `env from/to`).
- **Numeric tolerance — scores and bias:** full-sequence and per-domain scores and bias are printed with one decimal; a submission value passes if its absolute difference from the reference value is ≤ 0.06 (half a printed decimal unit plus floating-point rounding slack). This bounds a representation/rounding difference only; it is not a guarantee that every wrong scoring method is detected.
- **Numeric tolerance — E-values:** full-sequence, conditional and independent per-domain E-values span many orders of magnitude and are compared with a *relative* rule: a submitted E-value passes if |submitted − reference| ≤ 0.05 × max(|submitted|, |reference|), i.e. within 5% of the larger of the two magnitudes. This is the reference/denominator convention that fixes the acceptance boundary.
- **Numeric tolerance — average posterior accuracy (`acc`):** absolute difference ≤ 0.006 (half a printed 2-decimal unit plus rounding slack).
- **Exact text fields:** target name, target accession (`-` when absent), query name, query accession, and the target description column.
- **Rejected values:** any non-finite or unparsable numeric value (including `nan`, `inf`, `-inf`, `*`) fails the corresponding check; a negative or out-of-range domain index, or missing fields, also fails.

## Cross-file consistency
The query name, accession and length in every `LuxC.domtbl` row must equal the `NAME`, `ACC` and `LENG` of the profile written to `LuxC.hmm`.

## General
Missing files, unreadable or malformed content, and files failing to parse with a HMMER3-format reader are failed checks, not successful runs. The grader compares parsed scientific content only; it does not compare timestamps, command lines, file byte hashes, HMMER version strings, comment headers in the domain table, or trailing-whitespace/indentation differences.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
