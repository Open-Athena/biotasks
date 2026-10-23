# Transport and timeout findings

The stdin candidate delivers a 1,080,000-byte literal payload with exact SHA256 in real Docker. The original pinned executor fails with Linux errno 7 before delivery. Representative quoting, UTF-8, closed stdin, exit/trap behavior and cwd/file persistence match in both implementations. This confirms the transport mechanism and candidate delivery, not biological PR recovery.

## Timeout is a separate inherited problem

Probe004 records runnable Bash processes after the Docker client returns exit124. Baseline CPU ticks increase 36→67; candidate ticks increase 36→71 between observations. These are live, CPU-consuming processes rather than zombie entries. Both executors share the original `_run` behavior: a client subprocess timeout does not cancel the remote command.

This means a long-lived native validation sandbox can retain timed-out work unless its lifecycle explicitly terminates it. The experiment does not quantify the contribution to historical Scanpy/MNE/LAMMPS/MMseqs2 failures. A general timeout/cancellation fix needs its own comparison; the script-transport candidate does not fix it. For a bounded live transport comparison, use isolated owned sandboxes and remove each after its arm, including on timeout, so old work cannot contaminate later measurements.

## Evidence and limits

- `local-results.json`: 20 local adapter cases, with shell diagnostic/introspection differences disclosed.
- `attempts/001`: missing Docker CLI, no Docker operation/container created.
- `attempts/002`: pinned CLI worked, mutable image tag absent; zero owned containers, tool files removed.
- `attempts/003`: real Docker delivery and initial process-presence observation; state not measured in this first observation.
- `attempts/004`: same executor/image pins plus explicit process-state/CPU-progress observation.
- `probe-accounting.json`: all submitted jobs, one attempt each, terminal states, exact payload hashes, source checkpoints and allocated attempt CPU-hours.

Each job used only existing reserved TRC capacity with two allocated CPUs and 2 GiB and a 600-second maximum. Docker containers were sequential, 1 CPU/512 MiB/64 PIDs, network none, no host mounts. Every created container was removed and owned-container absence verified; downloaded tool files removed. The original immutable Python base-image cache remains shared input, not a task-built image. All four attempts together consumed 0.05442 allocated CPU-hours. Model calls/spend are zero. The fourth submission enforced measured prior allocation plus its maximum against a one-CPU-hour campaign ceiling.

The candidate changes only `DockerSandbox.exec`, leaves original `_run` unchanged and has not been promoted/applied to an actual repository pipeline run. Real failed-PR and successful-control comparisons remain required, with original tests and environment provenance preserved. This issue remains open.
