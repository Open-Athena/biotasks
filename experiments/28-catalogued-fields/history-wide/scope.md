# Research: evaluate pr_runtime across repository PR history

## Goal

Search merged PRs across the history of the same ten repositories used in #28, without a September or other lower-date cutoff. Build toward scalable automated task generation. The completed September run remains a separate baseline; do not present its two exports as the yield from all repository history.

## Discovery comes before execution

Create a frozen, deterministically ordered inventory of all merged PRs available as of a recorded cutoff. Preserve per-repository totals, pagination/cursor evidence, exact PR identities and unavailable metadata. Exhaustive discovery and exhaustive runtime validation are different milestones: do not claim either without its evidence.

Process that inventory in bounded, resumable batches. Report discovered, filtered, entered, paired-validation, exported and independently verified counts separately, with remaining backlog and failures visible. Do not silently replace a history-wide inventory with a latest-100 or latest-1000 sample. Historical environment compatibility remains a measured risk.

## Why removing the date filter is insufficient

The original #28 configuration set `since=2026-09-01`, `until=2026-09-30` and `limit=100`. Removing the two dates is supported configuration, but still limits the number of returned PRs.

At pinned Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`, `src/repo2rlenv/github.py:list_merged_prs` also limits the underlying `gh pr list` request to `min(limit * 3, 1000)`, applies dates client-side, fetches base SHAs, then stops after `limit` summaries. Raising the configured limit alone cannot enumerate more than the fetched 1000 rows. Splitting into old date windows alone does not bypass the cap because filtering occurs after fetching.

Source checked read-only on 2026-10-22: [exact pinned discovery implementation](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/github.py). No execution or upstream modifications accompanied this inspection.

## Agreed direction; concrete changes must be checkpointed before use

1. Remove the September dates. This changes the search scope using supported configuration; it is not a task repair.
2. Add the minimum deterministic discovery/pagination adaptation needed to traverse history beyond upstream's 1000-row fetch ceiling. Checkpoint the exact implementation and fixture evidence before use. Preserve all original native eligibility, patch splitting, paired tests and export/grading behavior. This is a proposed upstream discovery modification, not unchanged-source execution.
3. Add explicit batch/progress checkpoints so a finite execution budget leaves an auditable backlog. Determine whether upstream can consume this manifest without further source changes before implementation. Do not assume this interface exists or promise automatic recovery from the aborts observed in #28.

Keep source, model, bootstrap and verifier settings comparable to #28 unless a separate change is explicitly agreed. Only upstream's own model calls are permitted. No additional LLM repair loop, manual dependency fixes, parser/transport repairs, candidate handpicking or replacement repositories are part of this scope.

## Stages and decision points

- First establish full-history discovery and per-repository candidate counts using read-only GitHub metadata, without builds or model calls. Record any incomplete enumeration.
- Use those counts and the #28 failure boundaries to choose a concrete first runtime batch and budget. A full-history sweep could be substantially larger than the prior experiment; its cost is not inferred from discovery counts alone.
- Run only after the discovery adaptation and a new execution budget are agreed. Keep independent base/oracle control time separate from generation and retain tracked-test versus clean-command results.

## Budget and publication state

The user approved the history-wide direction, proposed a **$100 total OpenRouter budget**, and explicitly requested reopening #28 on 2026-10-22. Conservatively treat $100 as the ceiling for the entire issue, including the existing $5.975286 baseline: **$94.024714 remains**. Failed attempts count. Discovery metadata uses no model calls. Keep the baseline scientific yield separate from later runs even though their costs share this ceiling.

Retain Sonnet 4.6, no fallback, temperature 0.2, 2048 output tokens and at most 20 bootstrap turns for comparability. Keep the prior per-repository $5 stop policy unless explicitly revised. Track actual per-request charges serially and reserve enough remaining campaign budget for the next request before dispatch. The $100 authorization does not authorize exceeding $100: if a sufficiently conservative per-request cost bound cannot be established, stop before the uncertain request. A local cost observer is not a provider-enforced billing cap; record the concrete enforcement method before model work.

Use only previously authorized existing reserved TRC CPU capacity; no new paid workers or accelerators. Size finite batches and their CPU/time allocation after the merged-PR counts and discovery interface are known. Do not treat $100 of model budget as unlimited runtime-validation capacity. Separate independent control time from generation.

The user requested reopening the existing issue, not creating another issue. Preserve the original September protocol/results unchanged and retain this scope separately. Read-only counts are complete: **23,285 merged PRs** across the same ten repositories, with no date filter. This is not a paginated inventory, eligibility assessment or validation result. Builds/model calls/validation wait for checkpointed concrete inputs and the minimal discovery implementation. No extra model repairs are authorized.

## Initial all-history count observation

| Repository | Merged PRs |
| --- | ---: |
| samtools/samtools | 735 |
| scverse/scanpy | 1941 |
| macs3-project/MACS | 157 |
| OpenMS/OpenMS | 5671 |
| lammps/lammps | 3367 |
| matchms/matchms | 435 |
| opencobra/cobrapy | 590 |
| soedinglab/MMseqs2 | 87 |
| mne-tools/mne-python | 7888 |
| OHIF/Viewers | 2414 |

Counts were read using one authenticated GraphQL metadata request on 2026-10-22. No PR-count or merge-date filter was applied. Full cursor traversal, eligibility and native execution remain pending.
