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
