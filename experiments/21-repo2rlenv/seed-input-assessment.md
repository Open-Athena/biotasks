# Seed-based recipe input assessment

Source inspection at Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No seed generation, model calls, or code execution is established by this assessment. These are separate input cohorts, not additional attempts for each repository.

| Recipe | Required input in the pinned implementation | Biological preparation needed |
| --- | --- | --- |
| SETA seed2synth | JSON/JSONL objects with source, title, question_text; loader accepts at most 8 MiB | Select attributable biological workflow questions, preserve source terms and exclusions, and distinguish supplied biological data from newly synthesized examples. |
| SETA evol | Existing Harbor parent bundles | Use independently validated parents; retain parent identity and distinguish related variants from independent tasks. Our 19 PR-diff exports are not yet validated parents. |
| DataArc | Harbor directories with instruction.md, solution/solve.sh, task.toml; text-only assets, at most 400,000 bytes per parent | Prefer small, validated biological tasks with complete fixtures. Loader truncates selected seed-file excerpts to 3,500 characters; check that scientifically necessary context survives. |
| TMax | Native sampler settings selecting existing legacy domains/languages | Taxonomy has scientific_computing and data_science but no dedicated biological domain. Inspect sampled inputs before counting biological coverage; a biological taxonomy extension is a separate intervention. |
| Endless Terminals | Native sampler settings selecting existing categories | Categories and independently drawn scenarios are generic terminal workflows. No native biological-context selector was found. Preserve generic baseline results separately from any biological sampler adaptation. |
| TerminalWorld | info.json and recording.txt pairs; transcript at most 160,000 bytes, metadata at most 64,000 bytes | Find a real, eligible biological terminal recording with enough environment/input context. The loader labels inputs as public Asciinema recordings, so do not fabricate a transcript or disguise a locally authored demonstration as public evidence. |
| SCALER | Family mapping with name, logic_description, generate_testcase, params, difficulty_dict, solutions; aligned Python/C++ references | Build an explicit biological algorithm family with an independently checked reference and answer contract. Generated instances are synthetic algorithm inputs, not observed datasets. |
| FrontierSmith | Seeds with id, title, problem, source, license; optional family | Select a biological optimization problem with explicit feasibility, objective, and meaningful competing solutions. Treat generated inputs as synthetic unless observed-data lineage is actually supplied. |

DataArc strips several benchmark-canary strings when loading source text. That transformation does not grant training permission or remove benchmark exclusions. Eligibility must be checked against the original parent before loading, and the original source and its restrictions must remain preserved.

Relevant pinned implementation paths under `src/repo2rlenv/pipelines/recipes/`: terminal/runner.py, seta_evol/recipe.py, dataarc/recipe.py, tmax/sampler.py and taxonomy.json, endless_terminals/sampler.py and taxonomy.json, terminalworld/source.py, scaler/families.py, frontiersmith/models.py. The existing applicability matrix remains an inspection ledger; this assessment does not change any route to executed or accepted.
