# Native inline cache identity

## 2026-10-24 — frozen source/fixture comparison

Started from main 2a1950d239f1ada467c35393991dac87debe35f7. Checked official upstream HEAD 4b29471c3b280e752e7ab4f3452ae455a9097094 (0.9.4), acquired three files through ordinary authenticated public GitHub reads, and verified Git blob plus SHA-256 identities. The four relevant writer/parser/recipe/reader functions remain identical to pinned upstream.

Frozen source/fixture protocol and generic lookup-only candidate before execution. Candidate compares repository identities case-insensitively, validates cached metadata, and rejects ambiguous valid recipes. It reuses upstream rendering; no build/install/test command is altered. Copied the 12 original public OHIF task bundles and original bootstrap JSON from #35, verified every byte/mode against its original acquisition, and recorded inventories in original-inputs.json. No runtime or metadata candidate execution yet; no new allocation, model calls or capacity.

## 2026-10-24 — fixture and real metadata results

All ten function-level fixtures passed. Lowercase and single option-hashed caches preserve the exact original recipe; mixed-case/default and legacy roots resolve under the candidate; absent/conflicting repo/ref metadata remains unavailable; multiple matching option slots are rejected rather than silently selected. Current upstream 0.9.4 has the same relevant function bodies as the pinned baseline, so updating alone does not address this source-level mismatch. Function fixtures do not execute a whole newer pipeline.

On all twelve unchanged OHIF copies, original pinned native preparation failed with no changed files. The explicit in-memory lookup-only candidate prepared all twelve via the same native API, changing only 24 Dockerfile/task.toml files. All 96 instruction/oracle/grading assets and parsed grading/resource/timeout contracts match originals. No alias, dependency/installation repair, command execution, model call or Docker operation occurred. This is metadata preparation only; image building and controls remain untested for the candidate.

Froze deterministic candidate/source bundles (120 candidate files and 27 source/notice files; 848,955 compressed bytes). Source notices cover original/current OHIF acquisition and every selected task base/head, plus Repo2RLEnv. Bounded text/archive credential/binary scans passed. Prepared a ten-object 963,760-byte snapshot for reviewed, append-only HF publication; no new runtime reservation or spending admission.

All ten HF objects verified anonymously, with member hashes and no overwrites. Removed original/baseline/candidate/current-source working copies after verified preservation (see completion-status.json). Remaining bounded bundle/staging copies have explicit cleanup conditions. No model calls, remote jobs or task-owned /tmp evidence. Candidate remains experimental and runtime untested; issue stays open for review.

After #37 consumed and archived its selected package, removed the redundant compressed candidate/source bundles (848,955 bytes). Verified copies remain in the immutable local publication staging and canonical public HF snapshot. #38 can restore from that manifest instead of relying on obsolete working-copy paths.
