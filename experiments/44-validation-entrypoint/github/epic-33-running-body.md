Build an unattended path from official Repo2RLEnv PR candidates to reproducible, independently controlled task bundles, preserving original grading without human/LLM per-task repairs.

**Current status:** bounded mechanism experiments through #43 are preserved. #44 has a published validation entrypoint implementation with 34 passing offline tests; its serial unchanged-reference native comparison is running. Main still provides only prompt inspection. The broader generation/validation objective remains active. [Current acceptance audit](https://github.com/Open-Athena/biotasks/blob/64ea12e0/experiments/33-unattended-validation/completion-audit.md).

- #34–#35 demonstrated fixed-handle recovery, offline dependency reconstruction, independently controlled native execution, verified HF archival and owned cleanup.
- #36–#39 prepared twelve OHIF exports with unchanged grading, isolated a missing-pnpm inline recipe, and recovered original #5996 controls using eighteen recorded bootstrap actions: nop 0/oracle 1, all 26 F2P and 1189 P2P, clean oracle exit.
- #38’s generic controller reproduced twelve positive Cobrapy pairs, with two clean whole oracle commands. Scanpy stopped at apt prerequisites. #40 found unchanged Scanpy replay transfer unsupported; old timeout trials remain ungraded.
- #41–#43 measured writer survival into retry and through Docker stop grace. Transient holes appeared; final logs were hole-free. New Harbor source removes the retry, but its native finite case failed at missing Buildx before a writer. Upgrade cancellation and historical Scanpy causation remain unproven.

**Coverage:** historical #28 counts remain 83 exports, 82 ever-positive and 67 ever-clean. Follow-ups are separate attempts. Twenty-five exports are publicly eligible; 58 Matchms exports remain withheld. No production-ready pipeline, cohort-wide portability or fresh Scanpy validity claim.

**Budget:** 6.364996 additional allocated CPU-hours used; 6.333333 CPU-hours outstanding for #44’s first primary/stop/cleanup jobs; no model calls or new capacity. Recorded paid cost $0; existing $10 archival reservation unreconciled. Operating ceiling $90, strictly below the $100 extra limit; reserved-CPU ceiling 32 hours. Model execution remains disabled. #44’s Cobrapy reference is running; Scanpy remains unadmitted.

Keep #28 closed and this epic/children open for review. Detailed logs and append-only HF snapshots live in comments; retain research branches and protected evidence.
