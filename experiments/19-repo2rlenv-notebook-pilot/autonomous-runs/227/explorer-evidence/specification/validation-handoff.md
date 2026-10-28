# Input derivations and endpoint lineage (private)

## Input provenance
- `/inputs/data/msa/LuxC.sto` (8548 bytes, sha256 e2cf20e9c15473a9ee33634415327e64b2e77b482dd6e43f759123c22f2e0edc) — from pinned revision `althonos/pyhmmer@90d2f28...` `src/pyhmmer/tests/data/msa/LuxC.sto`; staged byte-identically on both reference tests.
- `/inputs/data/seqs/LuxC.faa` (7302 bytes, sha256 7ce47aaed2c5e1eba1c683dc0be3efa11ee34038eb498cc09287c61c62b697d0) — same source revision `src/pyhmmer/tests/data/seqs/LuxC.faa`.
- The alignment has 13 member sequences (HMM `NSEQ 13`), the FASTA database holds 12 sequences; the reference domtbl has 12 data rows (every sequence reports ≥1 domain, each exactly 1). These measured counts are private; do not expose them as public expectations.

## Method-lineage facts (measured/cited)
- Builder effective configuration = pyhmmer 0.12.3 `Builder.__init__` defaults (plan7.pyx lines 638–665): architecture="fast", weighting="pb", effective_number="entropy", prior_scheme="alphabet", symfrac=0.5, fragthresh=0.5, wid=0.62, esigma=45.0, eid=0.62, seed=42. The source passes only `alphabet` (original.py line 52), so all defaults apply.
- Background = default non-uniform amino-acid background (`Background(alphabet)`, line 452, `uniform=False`).
- Pipeline effective configuration = `Pipeline.__init__` defaults (plan7.pyx lines 5471–5494): bias_filter=True, null2=True, F1=0.02, F2=1e-3, F3=1e-5, E=10.0, domE=10.0, incE=0.01, incdomE=0.01, bit_cutoffs=None, Z=None→auto (number of sequences searched = 12), domZ=None→auto. Source passes only `alphabet` and `background` (original.py line 93): no nondefaults.
- Alignment `#=GF GA/TC/NC` (LuxC.sto lines 7–9) propagate into HMM lines 17–19 (`GA -133.50 -133.50`, `TC -133.50 -133.50`, `NC -133.70 -133.70`) — hmmbuild copies the leftmost (ls-mode) pair from the semicolon-separated annotation. The public brief phrases this as "the cutoffs the builder copies from the annotated alignment" without exposing values.
- HMM name/accession/description derive from `#=GF ID LuxC` / `#=GF AC PF05893.5` / `#=GF DE Acyl-CoA reductase (LuxC)`.

## Reference artifacts (recorded, byte-pinned)
- `LuxC.hmm`: 187150 bytes, sha256 b025cef47b04917a83704604bd1785ef48e010b081b82fb4b2936d3849569c02, 1228 lines. Runtime-variable lines only: line 12 (`DATE ...`) and line 13 (`COM /work/reference.py`). All scientific fields replay-stable (outcome.json: cross-run differences confined to DATE/COM; CKSUM 395769323, EFFN 1.989990, NSEQ 13, LENG 400 matched the upstream packaged fixture).
- `LuxC.domtbl`: 4093 bytes, sha256 fc3da85a5d9a7c8bdb7ed7d3ff8d1114488e3707abf8f7311bd83a24186b563b, 15 lines (3 comment headers + 12 data rows). Byte-identical across both reference replays and across the removal test.

## Endpoint coverage ledger (source operations)
- call-20 (Alphabet.amino), call-26/27 (MSAFile.read), call-52/53 (Builder/Background), call-54 (build_msa): preparatory machinery feeding the HMM — output graded via LuxC.hmm.
- call-86/87 (open/hmm.write): serialization of endpoint 1.
- call-93/94/95 (Pipeline/SequenceFile/search_hmm): search machinery feeding endpoint 2.
- call-100 (print(ali)): **excluded** — display-only inspection of TopHits (hits[0].domains[0].alignment); its scientific content (score, hmm/ali/env coordinates, accuracy) is carried in the domtbl row for that hit; upstream also removed `LuxC.hmmalign.sto` because it reproduces this printed alignment verbatim.
- call-104/105 (hits.write): serialization of endpoint 2.
- `hmm.consensus` (source line 79): **excluded** — inspection of the built HMM; consensus residues and MAP annotations are embedded in the exported profile (header `CONS yes`, `MAP yes`).

## Answer-copy control (must hold in solver environment)
Verified-unused answer fixtures removed from the executed environment (removal re-validated by a passing controlled re-run):
- `pyhmmer/tests/data/hmms/txt/LuxC.hmm` (sha256 e7a4dd57...) — same profile parameters as the produced HMM, differing only in DATE/version stamps and missing COM line.
- `pyhmmer/tests/data/msa/LuxC.hmmalign.sto` (sha256 d0a997a8...) — verbatim copy of the printed first-hit alignment.
The solver environment must not contain these files (or any cached backup of them). The copies of LuxC.sto/LuxC.faa under `pyhmmer/tests/data/` are byte-identical to the declared inputs (input representations, not answers) and may remain.

## Unresolved validation questions (executable stage; uncalibrated)
1. HMM comparison strategy: line-by-line content comparison excluding DATE (line 12) and COM (line 13); whether to normalize whitespace on the excluded lines only. Whether per-field numeric tolerance (vs. exact rendered strings) is needed for cross-implementation submissions — HMMER prints fixed-precision fields, so exact-string comparison against the reference is plausible for the reference stack; tolerance for alternative implementations is unmeasured.
2. domtbl comparison: parsed-field comparison vs. exact fixed-width byte match; row order by decreasing full-sequence bit score (rank-encoding — verify order is enforced, not just the row multiset); whether the 3 comment header lines are required verbatim; E-value string rendering (e.g. `2.3e-169`, `1.8e-167`) — exact string vs. numeric-with-tolerance comparison uncalibrated.
3. No scientific non-identifiability is present: the build is seeded and deterministic from immutable inputs; domZ auto-detection depends on the number of reported significant sequences (self-consistent, not externally ambiguous).
4. Replay evidence: 2 fresh reference executions; domtbl byte-identical, hmm differing only in DATE/COM — but this is finite-run evidence on a shared rebuilt environment, not a portability proof.
5. Data licensing: repository test data derived from Pfam PF05893/UniProt; redistribution terms not independently reviewed — a construction-staging concern, not a scientific-definition blocker.
