Evaluate official Repo2RLEnv `pr_runtime` across ten popular repositories spanning the existing #5 biology-field catalog, using fixed inputs/settings and no additional repair loop. Earlier #25–#27 experiments are separate baselines.

**Current status:** all ten original attempts have finished. Reviewed evidence for every repository is archived with anonymous readback verification. Final cohort audits, cleanup and conclusion are in progress.

**Results:** two Scanpy exports; one verified task under the declared tracked-test criterion; zero clean whole-command oracle resolutions. The verified task retains ten shared untracked failures. The other export's controls timed out with no reward. Recorded OpenRouter charges total **$5.975286** across 140 calls; allocation was **20.031 CPU-hours** on existing reserved TRC capacity.

Bootstrap, acquisition/API, patch transport, test collection/parsing and timeout issues limited yield. No task/environment/parser/transport repairs, generation retries or replacement repositories were applied.

[Ten-repository results and limitations](https://github.com/Open-Athena/biotasks/blob/3113923d/experiments/28-catalogued-fields/cohort-report.md) · [Original protocol and budget](https://github.com/Open-Athena/biotasks/blob/599af492c20ebf2304dee8ce7513000baa537ede/experiments/28-catalogued-fields/protocol.md). Detailed run updates and logs are in the comments and their linked artifacts.
