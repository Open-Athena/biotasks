# Durable runtime artifacts

## 2026-10-23 — source assessment

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on `codex/research/35-durable-runtime-artifacts`. The first MACS diagnostic's exported Dockerfile refers to a local image ID that its verified cleanup removed. This establishes an artifact-availability question, not a fresh-worker execution result.

Source inspection found existing upstream registry and inline-recipe distribution. Verified eight relevant source files against the frozen package acquisition and Git blob identities; no package code was imported or executed. Favor these interfaces before building new distribution infrastructure. Documented a source-level unresolved-digest edge case and the need for actual retrieval/control evidence.

An initial check incorrectly compared the stored API-tarball digest with the separate codeload-archive digest and stopped before inspection. The existing acquisition record identifies the API archive (`7e387fbb…`) and verifies selected files by Git blob identity at the same pinned revision. Subsequent inspection used that recorded source tree and its per-file hashes. No inputs were changed or reacquired.

No registry credentials were inspected, no task variant was generated, no source package or remote job executed, and no image bytes were uploaded. This issue has no new budget allocation. The active #34 confirmation proceeds independently under its existing reservation. Next: assess the native inline recipe's actual cache requirements and registry prerequisites; checkpoint a concrete eligible retrieval comparison before any execution.

## 2026-10-24 — native preparation and frozen cold-worker comparison

Executed unmodified upstream inline preparation in a network/subprocess/credential-read audit guard after verifying all 353 package source hashes. Anonymous acquisition restored three already public phase archives (12,389,446 bytes); no Matchms bytes were acquired. Native metadata preparation produced 12 Cobrapy and one Scanpy export; 12 OHIF exports failed the case-sensitive cache lookup. MACS #742 failed separately because its bare image ID cannot resolve a native recipe; it is outside the cohort denominator. No aliases or source fixes were applied.

Froze Cobrapy #1482 by deterministic selection among the two previously positive, clean eligible tasks. The 16,881-byte package has ten files, eight original assets unchanged, and only native Dockerfile/distribution metadata changes. Resource helpers are byte-identical to #34 except the explicitly documented ownership-label and read-only identity instrumentation. Bounded checks verified native file identities, ownership-only recipe alteration, unsupported-stage rejection and syntax. These checks do not establish Docker runtime success.

Admitted one 4-CPU, 3600-second reserved-worker attempt (4 allocated CPU-hours maximum) plus 1/6 hour emergency cleanup before submission, within the epic's 32-hour allocation. Recorded source-worker receipts for exclusion; no credentials transferred. The protocol and input manifest freeze original controls, 300-second verifier and no repair policy. No model calls, new capacity or runtime submission at this checkpoint.

## 2026-10-24 — different-worker runtime completed

The fixed handle succeeded in one attempt, 257.642 seconds at four allocated CPUs: 0.28626888884438406 CPU-hours. Actual worker identity differed from both excluded workers, and all four original Cobrapy image references were absent before building. Native inline recipe built without repairs; nop reward 0/F2P 0 of 2 and oracle reward 1/F2P 2 of 2; both retained 17 of 17 P2P tests. Oracle inner command exit 0. Raw pytest logs independently confirm 2 failed/17 passed and 19 passed. All ten native task files and eight original grading/oracle/instruction assets remained unchanged.

Each arm rebuilt a different image ID from the same original/effective recipe; actual Git base, Python/platform and installed packages matched. The initial readback incorrectly required identical image IDs for its provenance gate. Retained that initial analysis unchanged; corrected the analysis to bind each build/identity capture to its own arm interval, verify actual recipe bytes, and cross-check raw trial/reward/test logs. No output, task, command or reward was changed or rerun. See readback-correction.md.

Primary cleanup verified no owned containers, controllers, images or volumes. Released emergency cleanup without submitting another attempt. Epic actual is now 4.715986666414473 CPU-hours, no outstanding CPU reservation, zero new model calls. Prepared an 18-object/333,590-byte append-only snapshot with original/current analyses and source notices; publication/readback is the remaining gate.

Filed #36 as an actual epic child for the separately observed generic cache-identity inconsistency. Its source/fixture work is queued, with no new execution allocation. Issue #35 remains open for review.

Verified all 18 HF objects anonymously, including nested archive/member hashes, with no overwrites. Removed 12,389,446 bytes of disposable public phase downloads; transfer caches and fresh readbacks were removed by the publisher. completion-status.json records remaining small verification inputs and native-preparation copies retained temporarily for #36, with explicit cleanup conditions. No task-owned /tmp evidence or remote jobs remain.

#36 completed and archived its source/fixture/metadata comparison. Removed the remaining native-preparation copies after its verified HF readback; original source phases remain publicly archived. Updated completion-status.json accordingly.
