# Validation handoff (private)

## Measured facts (evidence, not ground truth)
- Reference artifacts on record (same model, default FBA): `single_gene_deletions.csv` (sha256 576e00fe…, 137 data rows + header), `single_reaction_deletions.csv` (e2766a64…, 95 rows), `double_reaction_deletions.csv` (9169de53…, 4560 rows). Columns observed: `knockouts,growth,status`; empty `growth` fields paired with status `infeasible` (2 / 2 / 352 rows respectively); status vocabulary observed: {optimal, infeasible} only (structural observation, not a guarantee).
- Row counts are model properties: 137 genes, 95 reactions, 95 + C(95,2) = 4560 reaction sets (singletons from self-pairs are part of the double-deletion population per `deletion.py` line 208).
- Reference stdout (trial log, private): complete 0.874; PFK KO 0.704; b1723 KO 0.874; b1723+b3916 KO 0.704 — consistent with projections of tables 1/2 (PFK and b1723 rows) and defines the wild-type and double-gene values for table 4. stdout is cross-evidence, not an independent rerun.
- Replay observations (two fresh runs): identical headers, stable row counts, but differing byte hashes and differing row-multiset fingerprints. Explanation: (a) row order comes from Python set-of-frozensets iteration and is run-dependent — order is a scientific non-invariance target, comparisons must be order-free; (b) low-order float digits vary between solves (0.9166474637510491 vs 0.9166474637510509 etc.) — LP degeneracy/alternate optima; requires calibrated numeric tolerance, uncalibrated here. Tiny negative growth values occur (single tables min ≈ -3.74e-15, double min ≈ -6.79e-14) and must not be clamped if source fidelity is to be preserved.

## Input derivation (to be materialized by construction)
- Task input `inputs/e_coli_core.xml` does not yet exist as an artifact. Intended derivation: the "textbook" model bundled with the reference environment — cobra 0.32.1 package data `cobra/data/textbook.xml.gz` (SBML, BiGG id `e_coli_core`), i.e. exactly what `load_model("textbook")` returns in cobra 0.32.1. Materialize the decompressed SBML at the stated task-relative path, pin its identity (size/sha256), and verify that the solver-loaded model yields the documented 137 genes / 95 reactions / 4465 distinct reaction pairs. This is a proposed derived input, not yet built or validated.
- No other inputs. iJO1366 is not part of the task (only used by the excluded timing benchmark).

## Endpoint lineage
- Table 1 ← `single_gene_deletion(cobra_model)` (call-50). Table 2 ← `single_reaction_deletion(cobra_model)` (call-96). Table 3 ← `double_reaction_deletion(cobra_model)` (call-97). Tables 1–3 have existing reference CSVs produced by the reference script's append-only export (frozenset labels → ";".join(sorted(ids)), NaN growth → empty CSV field via pandas defaults).
- Table 4 (`pfk_knockout_optima.csv`) has **no existing reference artifact**. Construction must generate it by faithful recomputation of the original with-block calls (calls 32–44) on the same unmodified model: wild-type `optimize()`; PFK reaction knockout then optimize; b1723 knockout then optimize; b1723+b3916 both knocked out then optimize. No reference values for this file have been measured beyond the printed stdout optima; it needs independent generation and validation. `knockouts` label for the wild-type row is an empty field under this task's stated convention (the source has no label for it; this is a new, explicitly documented representation choice).
- Method facts (verified in cobra 0.32.1 source, cited in review): default `method="fba"`; growth = `slim_optimize()` objective value; `SolverError` → NaN + solver status; GPR-based gene knockout with isozyme tolerance; reaction knockout = bounds (0,0) both directions; double-reaction population includes singletons from {r, r} self-pairs; row order from set iteration is nondeterministic and scientifically meaningless.

## Exclusions (source-backed)
- iJO1366 double-gene runs and all timing prints (calls 26–83 timing parts): nondeterministic multiprocessing benchmark; narrative frames them only as such.
- Subset demo calls 54, 58, 87–88: covered by projections of tables 1–3 (same populations, prefix/positional slices, identical operations).
- `double_gene_deletion(genes[-5:]).round(4)` (calls 64–65): mechanics demonstration, value discarded (bare expression; not printed in script run); `.round(4)` is display formatting. Flagged as a judgment call — if validation deems this an eligible endpoint, it can only be recovered by faithful recomputation over the model's gene order (positional slice `genes[-5:]`); no reference exists.
- `.knockout[]` prints (calls 99–100, 108–109): projections of tables 2/3 rows.

## Unresolved construction/validation questions
1. Materialization and identity pinning of `inputs/e_coli_core.xml` (above), and confirmation that a solver rebuild from this file reproduces the declared gene/reaction populations.
2. Generation and independent validation of `pfk_knockout_optima.csv` (no reference artifact yet).
3. Comparison design (validation-owned): order-free row comparison; numerical tolerance for `growth` (unrounded doubles, LP degeneracy and cross-solver variation; tiny negatives must be accommodated rather than clamped); status-string comparison; treatment of the four table-4 rows (wild-type empty `knockouts` label).
4. Whether any status other than {optimal, infeasible} can occur for this model and knockouts (only the two were observed structurally).
5. Timing feasibility: full double-reaction sweep completed in ~12 s in the reference sandbox (600 s limit); solver-side portability to other LP solvers untested.

Tolerances, comparator code and pass/fail predictions are deliberately left to the validation stage; nothing here asserts equivalence of alternative stacks beyond the astronomical-unit conventions fixed above.
