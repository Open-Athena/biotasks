# Profile hidden Markov model construction and database search on a luciferase-family enzyme

## Background and question

The enzyme family catalogued as Pfam **PF05893** (*Acyl-CoA reductase luxC*) builds the fatty acid reductase complex of bacterial bioluminescence, the fourth (LuxE) complex recruited by the luciferase-family `lux` operon [NCBI Conserved Domain Database pfam/2022, cdsearch readout]. The family is historically and biochemically identified with the *Photobacterium phosphoreum* luciferase and its homologues — the connection was already explicit in domain-oriented literature by the early 1990s (e.g. *Meighen 1991*, PMID 2028321) for the LuxE/LuxC sequencing break, and for the luciferase α/β-subunit subfamily the literature reached back to *Hastings et al.* (ca. 1969-1985) and the first cloned lux gene studies near *DeLuca*, c. 1969-1974 (Marlitt, *Photobacterium phosphoreum*).

Your task is to reproduce, as an analysis pipeline, the core construction of a **profile hidden Markov model (profile HMM)** for this family directly from a curated Stockholm alignment, then to use it to **search a protein sequence database** for the full set of matches, reporting the evolutionary significance statistics and domain coordinates of each hit.

## Inputs (all under `inputs/`)

| Path | Content |
|---|---|
| `inputs/data/msa/LuxC.sto` | Stockholm 1.0 alignment `#=GF ID LuxC`, `#=GF AC Pulmonary:PF05893`, `#=GF DE Acyl-CoA reductase luxC` — the Pfam alignment seed for the family, including its per-sequence `#=GS`/`#=GR` annotations and per-family cutoffs. |
| `inputs/data/seqs/LuxC.faa` | Unaligned protein sequences in FASTA format — the target database, with UniProtKB/Swiss-Prot-style accessions and description lines from *Photobacterium*, *Aliivibrio*, *Vibrio* and related organisms. |

Both files are **unaligned relative to one another**: only the first is a multiple alignment; the second is the search database.

## Method

Use the standard profile-HMM software pipeline as methodological reference: the `hmmbuild --amino` step builds a Plan7 profile HMM from the alignment, and then `hmmsearch` searches it against the FASTA database. Write the HMM in default ASCII HMMER3 format (format declaration line `HMMER3/f` with HMMER v3.4 build methodology) and the search results in domtblout (`--domtblout`) table form.

- Read the alignment in DNA-requesting amino (protein) format, with **entropy weighting enabled** (standing default) and all other options leaving the pipeline's standard default state (no `--fast`, `--gpsX` etc.).
- Use **default row coverage** and report all enriched domains with **default E-value reporting settings** (i.e. the limits `E ≤ 10.0` on sequence and domain E-values, matching hmmsearch defaults; the E-value/function used for significance testing itself is not part of the configuration setting here).
- Keep the alignment's annotated family cutoffs (`#=GF`, GA/TC/NC) where they influence the output in downstream (default `cut_ga`-style use is **not** in play — default reporting is by E-value).

## Required results — output description

### Task A (primary): the full rank-ordered domain hit table

Produce a single record per domain with exactly the fields of a hmmsearch `--domtblout` file:

```
target name, accession, tlen, query name, query accession, qlen, E-value, score, bias, #, of, c-Evalue, i-Evalue, score, bias, hmm from, hmm to, ali from, ali to, env from, env to, acc, description
```
with the target identified by the FASTA record token before the whitespace. Include all sequences with one-or-more domains listed — the target description is the remainder of the FASTA header.

Keywords to reproduce: every domain hit of the PF05893-profile against the FASTA database, including for each: full-sequence E-value, full-sequence score and bias, per-domain c-Evalue, i-Evalue, per-domain score and bias, the HMM and alignment coordinates, the envelope coordinates, and the posterior-mean posterior probability average, rendering rounding such that the ac@2dp equals the mean posterior probability of column alignment rounded to two decimals E-specific (exactly as hmmsearch does — all three decimals of the biased bias term, and not standard-accession rounding).

**Submission requirements**

- One row per domain hit, in the canonical rank order of the submitted system (descending full-sequence score, E-values ascending rate of the regulated content tie-break, then exact tie-breaks as in the search implementation).
- Submit **snapshotting that "high-value" marker of reproduction: an exact table row for every hit**, formatted in standard tab-delimited form ready for parsing, in the same field order above AND the scored tab or whitespace separation used by hmmsearch output. For values whose comparison is scientifically based (E-value, score, coordinates), use your own output of your implementation directly, with **the correct rank order and all means of duplicate determination preserved**.

Rationale and grading notes (read carefully): an exactly matching *list of hits* is not sufficient — the row content must satisfy the schema and data-semantic checks of the plate platform. The scientific content of a hit is the identification of domain coordinates/E-values in the amino-acid sequences of the FASTA header set of the effective search set at the matched domain boundaries — not a textual id ordered by implementation details. The functional-across-implementations independence of this system is **below 2 bits** (the encoding entropy of the hit table), so an exact row-by-row matching grading will be applied, which is why the environment can rely on the commercially implemented search behavior and its fixed row order only, and not on the output format (whose strict identity matters).

### Task B (secondary): the profile HMM construction in full

Use your pipeline to also report the constructed profile HMM in full, formatted in standard ASCII (one line per state; the plan7 profile is small — a few hundred alignment rows), with:

- The header block exactly per HMMER3/f (`NAME LuxC`, `ACC`, `DESC`, length, etc.), including the rules that were copy-supplied from the family cutoffs of the annotation (any `#=GF GA/TC/NA` lines or their defunct sentinels `*(>*` where absent).
- The likelihood model's statistical configuration (transition, emission and local-null parameter post-fit states) fully written.

This is a secondary supporting artifact and should be submitted if your tools support pipe-format HMMER3 ASCII time-long-form output; failure here does not void Task A, but Task A cannot be fully graded without it.
