# MNE post-check time comparison

The prior frozen replay matched all 12 recorded bootstrap BASH exits 127, then the unchanged `cd /workspace && python -m pytest -v mne/` smoke check reached 28% and timed out at 300 seconds. That check was incomplete, and no image or PR14445 native validation was produced.

This one-attempt comparison uses the same source ref, base image, commands, Docker limits and worker. Only the two exact upstream post-bootstrap smoke/fresh test invocations receive 1,200 rather than 300 seconds. The recorded action limits and commands are unchanged; no `Assistant:` tails are stripped and no dependency or per-PR test repair is made. The original replay and result are preserved separately.

Execution uses existing reserved worker capacity, 4 allocated CPUs/16 GiB memory and disk, 3,900 seconds work plus 600 seconds cleanup in a 4,500-second Iris job, at most 5 CPU-hours. The prior two jobs used 0.72125 CPU-hours, leaving the sum under #32's 10-hour ceiling. The clone is pinned and read-only GitHub access needs no token. No LLM calls or new capacity. Timeout aborts later work and forces owned container/image cleanup. A passing smoke/fresh check would establish only usable reconstruction; PR14445 native validation remains separate. Failed/partial checks remain recorded failures, with no iterative repair.
