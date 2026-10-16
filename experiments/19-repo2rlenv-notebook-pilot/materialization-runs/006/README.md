# Materialization 006 — executed; numerical validation pending

GLM submitted three complete candidates through submission/revision tools, without an exploratory shell. Controlled execution rejected the first candidate's file-inventory prefixes and the second candidate's sparse-matrix dimension check. GLM repaired both; no generated scientific artifact was manually edited.

The final candidate derives four public inputs (the two unchanged provider count matrices, cell groups and gene identities), projects the existing private marker table, and runs a separate oracle without access to the reference or author workspace. All declared inventories and original-input identities passed. The oracle wrote 398,259 rows across 17 supplied groups and 23,427 tested genes. It reported 14.4 seconds through output writing; the controller measured 24.16 seconds for derivation plus isolated execution. These are execution facts, not numerical acceptance evidence.

The final archive was download-verified and the small records were recovered with their original hashes. Controller cleanup passed; independent provider inventory found zero remaining owned sandboxes. Presentation copies are extracted from the unchanged candidate.

## Operator review before grading

The submitted question preserves specification 016's fixed-group scientific target. Input derivation selects metadata without marker-answer leakage. Oracle statistics are computed from the supplied inputs; expected answer values are not hard-coded. The generated reader contains permissive fallbacks for malformed matrices, but none emitted warnings on the immutable, hash-verified provider files used here. This is not evidence that the reader is suitable for arbitrary damaged inputs. The worker's rationale includes unmeasured numerical hypotheses; the next stage must measure agreement and justify tolerances, rather than adopting those guesses.

Next: independent implementation from public inputs, deterministic grading calibration and scientific counterexamples, then native Harbor controls and a blind attempt. No new release is validated yet.
