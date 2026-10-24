# Native published-Harbor comparison

## 2026-10-24: preparation

Issue #43 is an actual child of #33, from main 2a1950d239f1ada467c35393991dac87debe35f7. Reuse the #41 outer transport/ownership design at b5533ced and the verified published 0.24.0 acquisition from #42 at 6d359949. No admission or remote runtime yet. Compare both published versions serially with the same additional external observer, preserving native package source, 2/30-second writer, 5-second verifier deadline and resource contract. Keep the exact writer bytes; its legacy BIOTASKS_RUN_ID input marker retains the biotasks41 prefix while Docker/job ownership uses biotasks43 labels. No biological task or pipeline dependency changes.

## 2026-10-24: compiled pair and observer checks

Both published wheels are pinned (203 baseline / 369 candidate source/metadata/license files), with Tenacity 9.2.1. Baseline constraints retain 103 package versions from the verified #41 freeze; candidate records its own declared dependency closure. The first source acquisition stopped on a ZIP directory entry; it was corrected before any install/runtime and the note is preserved.

Compiled four synthetic cases and one fixed handle biotasks43-compare-0cae81dff1. Five lightweight preflight checks pass: real constructor with no creation effects, pair/old-writer identity and payload hashes, exact owned NUL policy, deadline/PID-reuse/zombie/absence guards, and read-only observation of a real finite local child. Test script/writer bytes are identical to #41; TOML contracts match between versions after removing only image references. Observers use the same script in both versions. Local tests used 2.25 sec wall / 0.21 CPU-sec / maximum RSS 25,616 KiB, no local Docker or native package execution.

Two-CPU / twelve-GiB / twelve-GiB-disk reserved-worker job proposed, maximum two CPU-hours plus 1/6 emergency cleanup. Task limits stay 1 CPU / 6 GiB / no network with five-second verifier deadlines. Package source is never patched; resource/ownership adaptation and observer are explicit. No admission or remote submission yet; input/policy checkpoint and read-only compatibility check precede reservation.
