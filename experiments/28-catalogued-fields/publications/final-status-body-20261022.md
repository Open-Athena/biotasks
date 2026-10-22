Evaluate official Repo2RLEnv `pr_runtime` across ten popular repositories spanning the existing #5 biology-field catalog, using fixed settings and no additional repair loop. Earlier #25–#27 experiments are separate baselines.

**Status: complete.** All ten original attempts, final audits, public evidence retention and task-owned cleanup are finished. Results: **two exports, one verified tracked-test task, zero clean whole-command oracle resolutions**. The verified task retains ten shared untracked failures; the other export's controls timed out without reward. Recorded OpenRouter cost: **$5.975286 / 140 calls**; reserved allocation: **20.031 CPU-hours**.

The findings identify acquisition/API, bootstrap, historical-environment, patch-transport, parsing and timeout limitations. This experiment does not establish a reliable production pipeline.

[Detailed conclusion, per-repo results and log/artifact links](https://github.com/Open-Athena/biotasks/issues/28#issuecomment-6352713291) · [Original protocol and budget](https://github.com/Open-Athena/biotasks/blob/7d52bb32e7d1abb867607cb7a15c179d2673ffdd/experiments/28-catalogued-fields/protocol.md). Detailed run updates remain in comments.
