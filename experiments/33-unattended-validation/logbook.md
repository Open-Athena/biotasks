# Issue 33: unattended validation

## 2026-10-23 — scope and budget

The user authorized independent weekend work with less than $100 extra spending and issue/HF records. Created epic #33, kept #28 closed and #29–#32 open, and started from main `2a1950d239f1ada467c35393991dac87debe35f7`. The operating ceiling is $90 across incremental billed services, leaving a $10 margin. Initial work uses no model calls or new paid capacity; paid model execution stays disabled until conservative request-cost reservations and actual provider reconciliation are implemented. The first remote stage may use at most 32 additional allocated CPU-hours on existing reserved TRC CPUs. Research inputs and outcomes remain separate from prior experiments.

## 2026-10-23 — source inspection changes the diagnosis

PR742's original exported `environment/docker-compose.yaml` maps PyPI and GitHub hosts to `0.0.0.0`. This is the pinned upstream answer-leakage guard, not an accidental missing Iris network setting. The #29/#31 Docker wrapper changes the resource/network properties but retains these task-provided `extra_hosts`. The candidate verifier replays a recorded editable install needing isolated build dependencies, so it conflicts with the preserved guard. Existing logs report refused package-index connections and `rebuild_incomplete` on both controls. Do not remove the guard to make a task pass. A generic build-dependency cache or distinct trusted preparation stage needs its own controlled comparison. No rerun or repair was performed for this finding.

The previous #31 license assessment relied on GitHub's null license metadata. #28 already retained actual MACS BSD-3-Clause notices at PR742's exact base and head, plus a reviewed original archive and upstream Apache-2.0 notice. Reuse those source notices and inspect the new artifacts before publication. This corrects the claim that source terms are wholly unknown; it does not automatically clear new downloaded data or an image release.

## 2026-10-23 — verified durable MACS archive

Preserved all eight reviewed #31 execution archives, source notices and provenance in the public HF bucket under `research/33-unattended-validation/2026-10-23/079a0f50dce9cb6c09984c6a4313b97eda8578ae859da0c12d2b143fa007185b`. All 31 objects passed fresh anonymous download and checksum verification, including nested archive member checks. The upload/readback completed in 21.06 seconds with peak RSS 115,400 KiB and exit status 0. Owned readback/cache directories were removed. No model calls or remote jobs were launched. Storage billing is not yet reconciled; retain the conservative $10 reservation. Original control failures remain unchanged.
