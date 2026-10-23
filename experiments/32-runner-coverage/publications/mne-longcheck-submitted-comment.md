🤖 Submitted one bounded MNE timing comparison from checkpoint `4b3bc656`, using the same recorded actions, pinned ref, base image, commands, Docker limits and worker as the prior replay. Only the exact upstream smoke and fresh-image invocations get 1,200 rather than 300 seconds. The original timeout record remains preserved; all 12 recorded `Assistant:` tails and exit-127 results remain unchanged. Seven pure routing checks passed.

The one-attempt job allows 3,900 seconds work plus 600 for cleanup, at most 5 allocated CPU-hours. Combined with 0.72125 measured from prior #32 jobs, this stays under the existing 10-hour ceiling. No new capacity or model calls. A passing post-check would establish a usable reconstructed image, not PR14445 validation or task recovery. Results, archive readback and cleanup are pending.

[Protocol](https://github.com/Open-Athena/biotasks/blob/4b3bc656/experiments/32-runner-coverage/mne-longcheck-protocol.md).
