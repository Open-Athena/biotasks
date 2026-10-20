# Bioframe release 001 — published and fresh-download verified

Published publicly to [gonzalobenegas/biotasks-notebook-pilot-issue-19-bioframe](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-bioframe/tree/1dd40a82a3bfc8741162ff37c4726ea84dd58405).
A forced fresh download of that immutable commit verified every release file,
executable mode and the exact native-tested task bundle.

- Final scientific controls: 15/15 (grading 004).
- Native Harbor oracle: 1; no-op: 0; blind GLM-5.3 Terminus-2 solver: 1, without exceptions.
- Blind trial: 210.21 seconds overall (about 3 minutes 30 seconds), seven successful model requests, all five verifier checks passed.
- Bundle: `sha256:44e68b961e2d5dee6b0ea445f34f5803eabb6198c6aa09d0d6a3420673ad0fa6`.
- Native source: `de7c881b585380b2a415e4fc1ea9b24e4877a540`; publication runner: `8fa9d0e`.
- All three native trial sandboxes are absent on independent provider readback; host and task SUCCEEDED.

This is a transfer experiment on one additional notebook. All generated task
science and repairs came from versioned GLM workers; no operator patched a
scientific artifact. The workflow needed operator recovery after general
orchestration/probe defects, so it is not a demonstrated fresh unattended
end-to-end run. Recovery timings exclude their prerequisites. One solver attempt
and a finite probe suite do not establish benchmark performance, universal
software portability, arbitrary-input oracle correctness or exhaustive detection
of wrong results. Authoring and solving used the same model family.

The upstream advisory label remains unverified because its standard quality-loop
profile was not run; separate executed BioTasks scientific/native evidence is
provided. Source MIT, ENCODE and JASPAR CC BY 4.0 notices remain intact. The first
publication attempt failed before upload on an unsupported SDK argument; readback
confirmed only initial `.gitattributes`. Both its original receipt and the
successful second receipt are preserved. Issue 19 remains open for user review.
