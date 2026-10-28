# Build a profile HMM from a multiple sequence alignment and search a protein database

## Objective

You are given a curated multiple sequence alignment of the LuxC protein family (acyl-CoA reductase, Pfam entry PF05893) in Stockholm format, and a FASTA file of full-length LuxC-family protein sequences. Your job is to reproduce the two terminal products of this analysis:

1. **A profile hidden Markov model (HMM)** built from the alignment, in HMMER ASCII profile format.
2. **A domain-search result table** produced by searching the protein database with that profile HMM, in the tabular domain format that HMMER's `hmmsearch` writes (domain table, one row per reported domain).

## Supplied inputs

- `inputs/data/msa/LuxC.sto` — the multiple sequence alignment in Stockholm 1.0 format. It carries Pfam-family annotations (`#=GF ID`, `#=GF AC`, `#=GF DE`) and scoring cutoff annotations (`#=GF GA`, `#=GF TC`, `#=GF NC`). The alignment's family name, accession, description and annotated GA/TC/NC cutoffs must be carried into the built HMM, exactly as HMMER's model builder does when constructed from an annotated Stockholm alignment.
- `inputs/data/seqs/LuxC.faa` — the protein sequence database to search, in FASTA format (UniProt-style headers).
- A compatible reference environment (Python 3.13, pyhmmer 0.12.3 providing HMMER 3.4 behavior) is available and may be used, but software choice is open: any implementation that produces the scientifically equivalent profile and domain table under the contract below is acceptable.

## Methodology (consequential — must match)

**Model construction.** Build a Plan7 profile HMM from the alignment using standard HMMER3 model construction with default parameters — i.e. the configuration HMMER's `hmmbuild` uses when invoked without options: fast model architecture determination (match columns assigned by residue-occurrence threshold 0.5), relative sequence weighting, effective sequence number estimated by relative entropy, and alphabet-based Dirichlet mixture priors, against the standard non-uniform amino-acid background model.

**Profile search.** Search the sequence database with the built HMM using the default HMMER3 accelerated pipeline — i.e. the configuration of `hmmsearch` without options: MSV/Viterbi/Forward acceleration filters at their default thresholds (permissive 0.02 / 1e-3 / 1e-5), composition-bias filtering and null2 score correction enabled, and reporting/inclusion by **E-value thresholds, not model-specific bit cutoffs**: per-target and per-domain hits reported at E-value ≤ 10, included at E-value ≤ 0.01. The per-target E-value must be computed with the search-space size Z equal to the number of sequences in the searched database, and the per-domain E-value with the number of significant sequences found.

## Required outputs

Write exactly these two files:

### 1. `outputs/LuxC.hmm`

The profile HMM in HMMER3 ASCII profile format (`HMMER3/f`). Requirements:

- Header fields must state the alignment-annotated name, accession, description and GA/TC/NC cutoffs (trusting the input annotations), the model length, the amino-acid alphabet, the annotation flags (RF/MM/CONS/CS/MAP) and the number of aligned sequences produced by the construction.
- The file must contain the calibrated local-mode statistics (MSV/VITERBI/FORWARD), the null-model composition line, and for every match state of the model: the emission probabilities over the 20 amino acids in the fixed order A C D E F G H I K L M N P Q R S T V W Y, the insert-state emission line, and the seven transition probabilities (m->m, m->i, m->d, i->m, i->i, d->m, d->d), together with the per-state consensus residue, consensus match and map annotations, ending with the null-model insertion line.
- Values are the natural units of the format: each model parameter printed in the composition line, the match-state and insert-state emission lines, and the per-state transition lines is the **negative natural-log probability of that model parameter**, written with five decimal places — a parameter probability of exactly zero is written `*` (and one of exactly one as `0.00000`). These are **not** log-odds or background-relative scores: no background division is applied in this file; log-odds relative to the background distribution are formed only later, inside the calibrated Plan7 search profile used for searching.
- The runtime-stamped `DATE` and `COM` lines are provenance only and are **not** part of the compared content; every other field and line is scientific content and must correspond to the reference computation described above.

### 2. `outputs/LuxC.domtbl`

The domain-search results in the tabular domain-table format that `hmmsearch` produces (with `--domtblout`): three comment header lines describing the columns, followed by **one data row per reported domain** — a domain being a single significant match of the profile to one region of one target sequence. Requirements:

- Each data row has the 22 fixed-width fields followed by the free-text target description, in the standard order: target name; target accession ("-"); target length; query name; query accession; query length; full-sequence E-value; full-sequence bit score; full-sequence bias; domain number and total domains for that target; domain c-Evalue and i-Evalue; domain bit score and bias; hmm coordinates (from, to); alignment coordinates (from, to); envelope coordinates (from, to); mean posterior accuracy of the domain alignment; description of target.
- The **target name** is the first whitespace-delimited token of each FASTA header (e.g. a UniProt-style identifier such as `sp|P19841|LUXC_PHOPO`); the description is the remaining text of that header.
- **Row order encodes rank**: rows are ordered by decreasing full-sequence bit score (hmmsearch's canonical ordering); this ordering must be preserved.
- The rows report exactly the domains passing the reporting thresholds of the pipeline described above (all sequences may or may not yield hits — report what the method yields, not an assumed number of rows).
- E-values are reported in the format's scientific notation, and scores in bits, as the format's fixed-precision rendering; these must correspond to the reference computation.

## Constraints

- Offline environment; no network access.
- Reference implementation environment: pyhmmer 0.12.3 (HMMER 3.4), Python 3.13.
- Time limit: 600 seconds. Resources: 4 CPUs, 8 GiB memory.
- Do not modify the supplied input files; the profile must be rebuilt from the alignment, not sourced from any precomputed HMM fixture.
- Numerical comparison tolerances and exact formatting/width conventions are provisional until the executable validation stage; the requested quantities, populations, ordering and field meanings above are the binding scientific contract.

## Acceptance rules

# Acceptance rules — LuxC profile HMM build and domain search (addendum)

## Output files

Produce exactly two files at the declared output root: `LuxC.hmm` (HMMER3/f ASCII profile) and `LuxC.domtbl` (hmmsearch domain table). No other file names are accepted; a correct file placed under an extra `outputs/` subdirectory is at the wrong declared path.

## Numeric comparison convention

All numeric fields are compared as parsed values, not as raw bytes:

- Every field is taken as a whitespace-delimited token; the reference's own printed precision defines the scale.
- A submitted value is accepted if and only if it differs from the reference value by at most half a unit in the last printed decimal place of the reference token (`1e-9` relative guard against binary rounding in the bound itself). This boundary is exact: adding or subtracting one unit in the reference's last printed place is rejected; printing additional digits of the same quantity (e.g. `2.07294` as `2.072940`) is accepted, since it preserves the decoded value.
- Tokens that are plain integers in the reference (lengths, coordinates, counts, checksum) require exact integer equality — the number of sequences, model length, target/query lengths, state indices, hmm/alignment/envelope coordinates, domain numbers and the CKSUM are all exact.
- `*` is a format token, not a number: a `*` in the reference must remain `*` in the submission at the corresponding position. A `*` must never be treated as zero (or vice versa), and nonfinite or unparseable values fail.
- Non-numeric tokens (names, accessions, the amino-acid letters, the per-state MAP/CONS/CS/RF/MM annotation tokens) require exact string identity.
- The `DATE` and `COM` lines of the profile, and the bracketed HMMER version stamp on the first line, are runtime provenance and are excluded from comparison; every other line and field is compared. The domtbl file is compared in full.

## LuxC.hmm — what is compared

1. First line declares `HMMER3/f` (the trailing bracketed version stamp is not compared).
2. All other header fields, in the reference's field order: `NAME` (luxC), `ACC`, `DESC`, `LENG`, `ALPH`, flag lines `RF no`, `MM no`, `CONS yes`, `CS no`, `MAP yes`, `NSEQ`, `EFFN`, `CKSUM`, the `GA`/`TC`/`NC` cutoff lines, and the three calibrated statistics lines `STATS LOCAL MSV`, `STATS LOCAL VITERBI`, `STATS LOCAL FORWARD`. `NAME`, `ACC`, `DESC`, `GA`/`TC`/`NC` and `NSEQ` must also equal the annotations and sequence count of the supplied `#=GF` Stockholm alignment (the alignment's `#=GF GA/TC/NC` first pair, before the first `;`, is what HMMER carries into the header).
3. The amino-acid alphabet line fixing the emission order `A C D E F G H I K L M N P Q R S T V W Y` and the transition-order header line `m->m m->i m->d i->m i->i d->m d->d`.
4. The three null-model lines (COMPO emission line, null-model insert emission line, null-model transition line, ending with `*` where the reference has `*`).
5. For each of the `LENG` match states, in state order: the match-state line (state index, the 20 emission scores, then `MAP` index and the four annotation tokens `CS RF MM CONS`), the insert-emission line and the seven-transition line, including the final state's terminal transition line.
6. The model block is terminated by `//`; the line structure (token counts per line type) must match the reference writer's layout, with no extra or missing fields.

## LuxC.domtbl — what is compared

1. The three `#`-prefixed comment header lines, exactly as the reference writer emits them.
2. The number of data rows and their order (decreasing full-sequence bit score — hmmsearch's canonical domain-table ordering).
3. Every row, field by field: the 22 fixed fields (target name, accession `-`, `tlen`, query name, query accession, `qlen`, full-sequence E-value, bit score and bias, domain number `of` total, c-Evalue, i-Evalue, domain bit score and bias, hmm from/to, ali from/to, env from/to, mean posterior accuracy) and the free-text target description. Integers and E-values per the numeric rules above; description text exactly.
4. Grounding to the database file: the target name is the first whitespace-delimited token of a FASTA header in the supplied database; `tlen` equals that sequence's ungapped length and the description equals the remainder of that header.

## Cross-checks

- The submitted domain table must be consistent with the submitted profile: query name/accession equal `NAME`/`ACC`; `qlen` equals `LENG`; hmm coordinates within `1..LENG`; alignment and envelope coordinates within `1..tlen`; domain numbers running `1..n` within each target; rows in non-increasing full-sequence bit-score order; and every reported full-sequence E-value at most the reporting threshold 10 (the default hmmsearch E-value reporting rule).

## Duplicates, missing values and malformed content

Missing files, empty files, non-UTF-8 content, truncated model blocks, rows with fewer than 23 fields, duplicated rows standing in for missing distinct hits, nonfinite values, and blank data lines all fail. Where the reference emits a value that can be parsed as a number, a submission that cannot be parsed at the corresponding position fails that check.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
