🤖 Source/offline investigation now has actual compiled-code evidence: [report](https://github.com/Open-Athena/biotasks/blob/1d3c7ff7/experiments/60-build-lifecycle/results.md), [full scripts/output/statuses/hashes](https://github.com/Open-Athena/biotasks/blob/1d3c7ff7/experiments/60-build-lifecycle/compiled-proof.json), [source audit](https://github.com/Open-Athena/biotasks/blob/1d3c7ff7/experiments/60-build-lifecycle/source-audit.json). Exact executed fixture checkpoint: 7b342465.

| Route | Pre | Post | F2P | P2P |
| --- | --- | --- | --- | --- |
| Original cleanup | Collection ERROR | Collection ERROR | 0 | 0 |
| Preserve base binary | FAILED | FAILED | 0 | 1 |
| Preserve HEAD binary | PASSED | PASSED | 0 | 2 |
| Replay original fixture build | FAILED | PASSED | 1 | 1 |

Eight real pytest processes used our own tiny C extension and the pinned original stage-builder, output slicing and status parser. Stage paths were relocated to owned scratch and global Git configuration redirected there. Explicit preserve/rebuild variants are modifications; full scripts retained. The rebuilding variant checks that HEAD and the source diff survive building. This establishes the mechanism, not arbitrary-command safety, a generic installed policy, Docker export/verifier parity, or a biological control pair.

Source review finds no project rebuild after native checkout/clean/patch, after the exported task overlay resets to base, or after the solver edits source before verification. Bootstrap inline replay occurs before the later base reset. Replaying arbitrary `rebuild_cmds` is not yet qualified: commands may reset/fetch source, install incompatible versions or reuse stale outputs. A source-diff check alone is insufficient. Next work must cover accepted command forms, build/import identity, failure/timeout behavior and all execution stages without per-task repair or extra LLM calls.

One admitted local command completed in 3.65s with 39,372 KiB peak RSS; scratch/binaries removed. Zero native/model jobs or new spend. #58 stays a preserved negative; no retry or new native/model admission. Existing budget and open-for-review status retained.
