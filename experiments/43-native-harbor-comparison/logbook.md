# Native published-Harbor comparison

## 2026-10-24: preparation

Issue #43 is an actual child of #33, from main 2a1950d239f1ada467c35393991dac87debe35f7. Reuse the #41 outer transport/ownership design at b5533ced and the verified published 0.24.0 acquisition from #42 at 6d359949. No admission or remote runtime yet. Compare both published versions serially with the same additional external observer, preserving native package source, 2/30-second writer, 5-second verifier deadline and resource contract. Keep the exact writer bytes; its legacy BIOTASKS_RUN_ID input marker retains the biotasks41 prefix while Docker/job ownership uses biotasks43 labels. No biological task or pipeline dependency changes.

## 2026-10-24: compiled pair and observer checks

Both published wheels are pinned (203 baseline / 369 candidate source/metadata/license files), with Tenacity 9.2.1. Baseline constraints retain 103 package versions from the verified #41 freeze; candidate records its own declared dependency closure. The first source acquisition stopped on a ZIP directory entry; it was corrected before any install/runtime and the note is preserved.

Compiled four synthetic cases and one fixed handle biotasks43-compare-0cae81dff1. Five lightweight preflight checks pass: real constructor with no creation effects, pair/old-writer identity and payload hashes, exact owned NUL policy, deadline/PID-reuse/zombie/absence guards, and read-only observation of a real finite local child. Test script/writer bytes are identical to #41; TOML contracts match between versions after removing only image references. Observers use the same script in both versions. Local tests used 2.25 sec wall / 0.21 CPU-sec / maximum RSS 25,616 KiB, no local Docker or native package execution.

Two-CPU / twelve-GiB / twelve-GiB-disk reserved-worker job proposed, maximum two CPU-hours plus 1/6 emergency cleanup. Task limits stay 1 CPU / 6 GiB / no network with five-second verifier deadlines. Package source is never patched; resource/ownership adaptation and observer are explicit. No admission or remote submission yet; input/policy checkpoint and read-only compatibility check precede reservation.

## 2026-10-24: native baseline measured; candidate prerequisite failure

Managed attempt completed with setup/driver exit 0 and both installed package source sets verified (203/369); baseline's 103 recorded dependency constraints match. Baseline finite case passes. Its timeout case has two writer starts and 34 PID observations after the final native exception, extending to +10.333724 seconds. Docker event ordering is TERM +0.557842, KILL +10.573770, death +10.628393, destroy +10.635841. Both writers survive during the stop grace period, then the container is removed. Ten writer samples / nine outside samples observe transient holes; final raw NULs zero. The observer is an instrumentation variant, separate from #41's original conjunction.

Candidate finite case fails before its writer: new Docker utils call buildx for the egress-control sidecar, which the minimal old toolchain lacks. Source and full native error bind the failure; this is an environment compatibility outcome, not cancellation evidence. Timeout is skipped under the declared finite prerequisite. No task/source/plugin repair or rerun. Candidate closure is distinct (two changed entries including Harbor, two added, sixteen removed); baseline versions match.

One attempt used 0.09966722223493787 CPUh. Raw runtime snapshot 68475d52b7608a42ee60973450834d8ddc5e20ba41005a5edc853aec3412d169 has verified anonymous readback; primary owned cleanup empty, public base preserved and cleanup reservation released. All eight stages complete; completed invocation leaves fourteen stage/budget files unchanged. Final summary/source archive and owned local duplicate cleanup remain.

## 2026-10-24: final preservation and cleanup complete

Final source/summary snapshot 7bc6cb3903d47630453f0e4ebab6dc22b91e9e5a05bd120618b4763dc661cfc1 has three objects/55 members, all anonymously verified. Package binaries/images/environments excluded; public package URLs/hashes and exact source-member identities retained. Removed 12,079,827 owned duplicate bytes after hash gates, keeping immutable final payloads and canonical runtime/summary archives with explicit review/rehydration cleanup conditions. Post-cleanup completed invocation left fourteen stage/budget files unchanged and submitted nothing. No /tmp paths, remote-owned resources or transfer caches remain. Candidate cancellation remains unmeasured because its finite prerequisite failed; no package/plugin/task repair or dependency promotion occurred.
