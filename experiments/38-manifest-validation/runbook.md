# Frozen-export controller operation

The native pipeline produced these existing task exports. This controller validates their frozen native inline packages; it does not discover PRs, generate tasks, repair installation commands or call a model. The two native families use identical code and data-only descriptors. The OHIF lookup candidate is a distinct reference-only variant with a source-bound prerequisite stop, not twelve fresh measured failures.

Executable checkpoint: `37c442b5`; frozen payloads and handles are in `runtime-plan.json`. Native source is pinned in `source-plan.json`. Input packages live under ignored `inputs-private/frozen/` until their snapshots are verified. The public policy excludes Matchms, images, environments, wheels and biological datasets. Credentials enter only the local transport through the approved CW source and the normal HF client; remote environment isolation supplies no service credentials.

Run the same foreground command from this branch using the existing Marin environment:

```bash
/home/exedev/projects/marin/.venv/bin/python -u experiments/38-manifest-validation/controller.py \
  --config /home/exedev/projects/marin/lib/iris/config/marin.yaml \
  --budget /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/33/experiments/33-unattended-validation/budget.json \
  --watch
```

The watcher is lightweight, holds only its experiment-local coordination lock, and polls unfinished remote work every five minutes. It does not need the shared local heavy-work lock for metadata and remote orchestration. Run substantive local checks/transfers under the shared-node limits when their footprint warrants it. Never start a second watcher concurrently. A missing or timed-out observation is not a failed task and does not authorize another submission; the server's existing-handle ERROR policy is explicit.

The adopted journal re-verifies bound code/policy/input/evidence files on every advance and resume. Do not edit them after admission. Reinvoke the exact command and journal after a local interruption. A deliberate restart test already resumed the first running handle with unchanged plan/submission hashes; final one-attempt evidence is a separate terminal gate. The first, unsubmitted receipt-schema failure is preserved in `pre-submission-failure.json`, not erased or counted as a remote attempt.

Each family reserves its primary and emergency allowance before submission. The second family waits for the first family's archive, anonymous readback and cleanup gates. Actual accounting is recorded even if it exceeds a reservation; any overshoot stops work. Original task settings remain one CPU, 6 GiB and a 300-second verifier. Two-CPU scheduling envelopes include a capped 0.5-CPU controller and 1.5-CPU build; use no accelerators or new capacity.

A common-prefix build failure stops that family before Harbor setup/controls. A per-task image build failure skips that task; a control-wrapper failure stops later tasks. Full nop/oracle trials run only when their reserve fits. Raw trial/reward files, stdout, source commits, actual immutable image IDs and original task file hashes are required for complete pairs. Positive pairs and clean oracle command exit are reported separately; job success is never a reward.

Publication generates its manifest from the frozen policy and verified archive. It recursively scans bounded text/archive bytes, uses a new manifest-hash HF prefix, refuses changed objects and verifies every object/member through anonymous download. Interrupted uploads resume the same manifest/intent with existing bytes checked, never overwritten. Unknown eligibility stops publication and subsequent family admission, leaving protected local evidence.

Cleanup deletes only owned Docker resources. A failed copy preserves the owned volume instead of deleting the only execution evidence. An emergency exact-worker cleanup requires a verified complete task execution archive and completed primary HF readback. Lost output identity, unavailable archive or unpreserved volume evidence is a protected recovery condition; keep the reservation/resources recorded and halt rather than fabricate a result or delete evidence. Do not remove unrelated descendants or shared public bases. Account for any cleanup attempt separately and archive its proof too.

After completion, retain manifests, receipts, result tables and source notices on this permanent research branch/HF; remove task-owned redundant acquisition/preparation/transfer copies only after verified durable replacements. No automatic issue closure or research-branch merge. A production extraction requires a separate branch from current main and validation.
