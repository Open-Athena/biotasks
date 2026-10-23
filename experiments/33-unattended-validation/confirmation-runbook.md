# Unattended confirmation prototype

This research prototype runs one frozen MACS diagnostic from recorded recipe inputs through independent controls, verified public evidence archival and owned-resource cleanup. It is deliberately bound to the existing run ID and manifests. It is not a general command for selecting new repositories or regenerating tasks.

Run from the issue-33 research checkout with the approved controller credentials available in its process:

```bash
PYTHONDONTWRITEBYTECODE=1 python experiments/33-unattended-validation/run_confirmation.py \
  --experiment ../34/experiments/34-offline-rebuild --watch
```

Only one watcher should run. The controller starts with frozen input verification, persists submission intent before invoking the bounded Iris launcher, then uses that fixed handle for observation. It polls no more often than every five minutes and has a three-hour local deadline. The remote combined job has its own two-hour deadline, four CPUs, 16 GiB memory and one attempt. No model or GitHub credentials enter the workload. No model is called during this path.

The remote job verifies its payload, replays the unchanged recorded commands and native checks, binds the actual resulting image digest into the candidate, verifies the twelve-file package and invokes the original nop/oracle commands. The resource wrapper captures the dependency receipt using a stopped networkless container before task startup. The original verifier timeout remains 300 seconds. The candidate's original instructions, tests, source patch, egress restrictions and grading contract remain byte-identical to the diagnostic export.

On terminal state, the controller downloads and hashes the output archive and checks its internal evidence. Job success, native build success, positive control pairing, clean oracle command and dependency provenance remain distinct fields. A negative scientific outcome can be preserved and cleaned. The committed publication policy covers only this public MACS source family; generated snapshots require nested text inspection, retained notices, exact archive identity and bounded size before append-only HF publication and anonymous readback. Cleanup admission checks that the verified HF receipt contains the exact execution archive.

If the controller is interrupted, stop or confirm termination of the old watcher and rerun the same command. The journal, intent, manifests and submission records are durable under `experiments/33-unattended-validation/private/confirmation-controller` and the issue-34 protected run directory. Do not delete these, create a new handle or resubmit because an observation failed. A timed-out API response is an unknown effect, not evidence that no job exists. Unknown submission outcomes are recovered by observing the same handle. If the journal or input hashes conflict, stop and preserve the error.

The first real restart was intentional: session40839 was interrupted during its sleep after a running observation, and session6070 resumed with identical journal and submission bytes. `confirmation-restart-proof.json` records the evidence and any still-pending post-restart observation. Synthetic interruption checks cover additional boundaries without creating remote work.

The first completed adopted-run example is recorded in `resume-demonstration.json`; it does not prove initial submission. The currently submitted confirmation must supply its own final receipts before this prototype is called an unattended success. After completion, retain journals, small manifests, allocation accounting and HF receipts; remove only verified disposable copies. Protected Matchms archives from earlier work remain outside this public route.

Limits include mutable bootstrap package sources, static build requirements only, no Docker image publication and a single compiled Python diagnostic. Wheel versions/hashes describe the recorded artifacts; they do not promise their future availability. Runner-specific completion and test-target selection remain separate research questions. No production pipeline or dataset release is claimed.
