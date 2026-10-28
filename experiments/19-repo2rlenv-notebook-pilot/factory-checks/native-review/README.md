# Post-native contract review candidate

Prepared on 28 October 2026; **not live-qualified or adopted into the frozen panel worker**. The original 237-file factory and its outcomes remain preserved. This candidate changes the stage graph and must receive a new source admission/checkpoint before execution. No new model request, campaign, sandbox, reward or scientific task edit was made here.

## Problem and upstream precedent

The existing BioTasks controller marks a task validated after native reference/empty controls pass and a blind solver returns a recorded reward. That proves less than whether the reward is fair. In the saved PyHMMER 227 trajectory, the solver executed two plausible precision flows that straddle the grader's rounding boundary. This is a contract concern, not a manually adjudicated replacement reward. The existing independent-solution and grader prompts already discuss write/read round trips; more wording alone would not close the missing review boundary.

Pinned Repo2RLEnv `55554430cd724efded1f5ad0ff98ebca5d88c0a6` reviews after a rollout and requires a legitimate outcome diagnosis before `usable`: [`quality/loop/runner.py`](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/quality/loop/runner.py), especially `validate_rollout_outcome`, the `r{revision}-after-rollout` review and final disposition checks. Its [`review prompt`](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/quality/loop/prompts/review.md) requires comparing a solver's first shared failure cause with the public contract. These sources were inspected locally at the pin. This candidate reuses upstream's `Review`, trial import/binding, reference/baseline contrast, citation and reward-consistency checks; it does not claim the standard upstream quality-loop label.

## Candidate stage graph

Existing preparation → setup/reference test → replay → specification/review → construction → grading/controls → native Harbor trials → **native contract review** → validated task or recorded stop.

The new GLM-5.3/native-high session receives complete, hash-bound task files, native results, solver commands/tool results, captured submissions and verifier reports. The existing lossless `ReviewPacket` serves read-only tools. Binary files retain an inventory/hash; their contents are not inferred. No extra input-size or response-size caps are introduced. Required approval citations cover the public contract, actual verifier output and the solver trajectory. Exact citations and reward consistency are necessary mechanical checks, not proof that the model's scientific reasoning is correct.

The reviewer cannot run a shell, recompute results, edit tasks, regrade, launch probes or repair. A sound review can admit either a legitimate success or a legitimate failure. A task defect/reward hack blocks admission; missing evidence stops with `needs_evidence`; infrastructure remains separate. The native reward and original files remain unchanged. The overall pipeline cannot reach `validated` before this review succeeds. Rechecking bytes, modes, missing/new files and links prevents a frozen review packet from approving different source evidence.

The session shares the original absolute campaign deadline, including the existing cleanup allowance, and creates no new sandbox. It adds no repair, solver attempt, longer reference/solver execution or model escalation. A diagnosed defect is a recorded stop; routing it into another repair is not implemented or authorized by this candidate. The general specification handoff now explicitly distinguishes consequential saved/reloaded representations from final exports, preserving intentional source quantization rather than prescribing a particular package or forcing every computation through text.

## Evidence and limits

- **100 focused checks pass:** new read-only session/evidence/admission tests plus controller transitions, existing native-control behavior and packaged prompt loading. The scientific worker and cloud provider were mocked; actual upstream trial/hash/citation validation ran on synthetic task files.
- [Offline capture of original 227 evidence](replay-227.json): all **55 files / 790,876 bytes** match the original archive manifest, including the entire captured trajectory; all three native trials bind to the original task. Full packet reconstruction and full trajectory reads match. Original rewards remain **1/0/0**.
- Ruff formatting/lint and `git diff --check` pass for changed code. No full repository CI claim is made.
- The first local test attempt exposed missing local Harbor hashing dependencies and stalled in a sandboxed thread/event-loop test; it was interrupted. Two focused retries identified missing `dirhash` and then `pathspec`. Four small pure-Python wheels were subsequently verified against the pinned upstream lock, and the final tests passed with elevated local execution. These were test-environment failures, not scientific worker outcomes. See [check receipt](checks.json).

**Still unproved:** GLM's actual judgment on 227, the candidate's end-to-end runtime/latency, source admission, live publication integration for a newly generated task and performance across the ten-domain panel. A model can still miss a scientific defect despite valid citations. Existing releases/viewer and the public 227 caveat are unchanged. Further live execution requires the pending funding decision and a distinct recorded worker version; preparing this candidate does not allocate funds.

## Release integration

Newly packaged tasks carry the `biotasks-native-contract-v1` admission requirement inside their bundle identity. The controller records the same profile. Scientific release checking revalidates the recorded review against the unchanged task and all native trials; publication requires the eight-stage completed pipeline, the exact accepting result, original worker submission and lossless input packet, all bound to the original archive. Missing, stale, unresolved or unarchived reviews cannot be relabeled as an assisted or legacy-profile release. The public evidence includes the accepting review and its identities, while the standard upstream quality-loop label remains unverified.

[175 focused integration checks pass](release-integration-checks.json), including compatibility with the original seven-stage publication path. A [read-only check of original227](legacy-release-227.json) keeps its original bundle identity and1/0/0rewards; it does not grant the new profile or clear its scientific caveat. No GLM/provider call or release upload occurred. This candidate still needs source admission and live execution.
