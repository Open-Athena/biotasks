# Candidate v1: not accepted

The authoring process used all 40 model requests and exited 1 after 268.382 seconds, preserving 26 generated/intermediate files. All forwarded requests returned HTTP 200. Unlike the bedtools run, it produced a task draft, native Scanpy reference code/output, and control artifacts. The reported native reference used Scanpy 1.12.4 and retained 2638 cells by 13714 genes. This is author-side evidence, not independent or native Harbor validation. No solver has seen this candidate.

The full event export was recovered and checked against SHA-256 `441318b35359568e2e5e3d04665cb9c22f069a6dd960ceb9a6d7c4189565cc11`. The two Dockerfiles were omitted by the small-text export suffix filter; their tool-input text plus recorded digest replacement were recovered and matched to their durable artifact-manifest hashes. Binary data/reference/control artifacts remain in private durable storage. `candidate-v1.json` preserves the exact recovered text, including defects; do not format or silently repair it.

## Required repair before acceptance

1. The instruction orders gene filtering before cell filtering; the native reference and seed do the reverse. Align the exact sequence with the seed, including its later strict `>200`, `<2500`, and `<5%` QC filters.
2. G1 grades approximate dimensions rather than exact cell/gene membership. Integer filter tolerances are unjustified; similarly sized but scientifically wrong subsets can pass. Recompute expected retained identities from the raw counts independently of Scanpy, require unique identities and exact membership, and allow harmless row/column reordering.
3. Gene-symbol suffix parsing is ambiguous for names that already contain numeric suffixes and rejects valid alternate disambiguation. Use the original stable gene IDs in an explicitly specified metadata column for lineage mapping, with symbols and duplicate handling described unambiguously.
4. The required boolean mitochondrial annotation is not actually checked. Specify its column and verify it against the input symbols. Prevent fabricated-but-internally-consistent counts/QC from earning dependent scientific credit; make QC/normalization depend on validated counts lineage.
5. Missing `counts` raises outside the grader's submission-validation guards. Test missing/malformed artifacts and nonfinite values explicitly. `test.sh` currently converts any grader failure, including dependency or infrastructure failure, into reward zero. Separate invalid submissions from verifier failures; unexpected verifier errors must remain ungraded.
6. Complete the validation plan and execute the deterministic grader against correct, partial, empty, wrong-threshold, corrupted-count/dependency, and same-shape-wrong-membership controls. Also test a correctly permuted artifact. Retain actual outputs and timings; no invented Harbor success. Native Harbor controls are still required afterward.

Retain the biological objective, observed inputs and five-minute solver budget. This repair is driven by scientific/contract review before any baseline attempt, not by solver performance. The second authoring session is the last allowed for this seed under the initial campaign budget.

7. Native Harbor integration established that separate verifier images must include an executable `/tests/test.sh`; Harbor does not supply it automatically in this mode. Ensure the tests Dockerfile installs that path, fixes grader/data paths consistently, and keeps these files out of the solver image. The v1 Dockerfile instead copied `/test.sh`, which would fail before scoring.
