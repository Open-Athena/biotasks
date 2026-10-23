# Issue 31: historical-builds

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — verified archive and syntax findings

Restored1,746,306bytes anonymously with original SHA256 verified; removed owned Xet cache. Checkpoint `b9056df3` syntax-only inspection completed in0.10seconds/21,128KiB under the shared heavy lock. Seven original extension-removal pairs reproduced from retained logs; three saved Dockerfile RUN bodies fail bash syntax checks. Saved reconstruction and historical rebuild are separate prerequisites. No recipe/test/container/model executed; exact findings in `lifecycle-findings.json` and `findings.md`.

## 2026-10-23 — compiled mechanism fixture

Added and ran a synthetic shared-library comparison through exact pinned native/export shell builders. Twelve cases cover missing binaries, correct-revision rebuilds, stale-binary false positives and fail-closed multiline rebuild failure. Original source hashes are verified; only filesystem roots are remapped. No environment recipe or biological source was repaired. All assertions passed and owned temporary files were removed. This supports a generic lifecycle hook investigation but is not an integrated candidate, graded-verifier check or live MACS recovery. Next: wire an opt-in hook through validation and export with explicit failure guards, then select one immutable original removal case and establish a declared baseline reconstruction procedure.

## 2026-10-23 — opt-in candidate wiring

Added reproducible candidate patch with `replay_bootstrap_rebuild=False` by default. Enabled mode uses recorded bootstrap commands for native stages and exported verification; empty command records are rejected and exported metadata records the procedure. Native setup is fail-closed and completion markers/exit status are checked before parsing. Export begins rebuild with a zero reward so timeout cannot inherit a prior success.

First fixture execution caught an incorrect clean-command list index (IndexError before rebuild); corrected index 5 to 4 and retained failed resource record. Candidate then passed all 12 compiled cases, including unchanged default script equality, revision-specific binaries, stale-binary negative controls and multiline build failure. AST parsing and patch applicability checks pass. These checks do not execute full pipeline wiring. Exported reset handling still inherits permissive upstream behavior; graded-parser and full native-outcome checks remain prerequisites. No biological repairs, model calls or remote execution.
