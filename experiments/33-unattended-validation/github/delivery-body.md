**Ready for review:** draft PR #63 provides a manifest-driven official Repo2RLEnv workflow: frozen discovery → built-in bootstrap/generation → export → deterministic controls → accounting, HF archival and owned cleanup. Codex is not in the execution loop. Main is unchanged; no merge or release.

**Decisive fresh result:** #66 completed the full workflow without per-task repairs: one NiBabel export, nop **0** / oracle **1**, target **0/9 → 9/9**, all **37 P2P tests pass on both sides**, oracle exit **0**. All four HF readbacks, owned cleanup and installed completed replay are verified. This covers the selected test-file command, not every NiBabel test or population yield. [Evidence](https://github.com/Open-Athena/biotasks/blob/0d7344963b050bf3743de14d4d6858039c2c6201/experiments/66-fresh-nibabel/results.md). #65’s DendroPy pair is tracked-positive but remains strict-ineligible because four unrelated failures persist. Earlier negatives are preserved.

**Validation and limits:** 186 local tests plus both GitHub CI checks pass. Official source stays pinned; approved wrapper/options are explicit. Import provenance (#56), argument/parser limits (#59), compiled rebuilding (#60) and subtest identities (#64) remain separate, undeployed research. Detailed conclusions, modification rationale and receipts are linked in comments.

**Final accounting:** **$2.196603 / 61 original model calls**, **14.892111111/32 allocated CPUh**; all admitted jobs terminal, CPU/model reservations zero, paid execution disabled. Existing **$10 storage reserve remains unreconciled**. Within the same $90 operating ceiling and strictly below $100 extra; no new capacity.

Keep epic/children and all pipeline PRs open for human review; #28 stays closed. No automatic additional run, merge or release.
