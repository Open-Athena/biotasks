# Sonnet comparison: valid action formatting, zero task exports

Claude Sonnet 4.6 produced **35 native agent actions with zero INVALID actions**, compared with GLM-5.3's 49 actions and 17 INVALID actions. Both arms produced **zero exports and zero verified tasks**. Changing the configured model improved compatibility with the action format in this sample, but did not establish a working task-generation pipeline or a quality/price advantage.

The upstream source remained `huggingface/Repo2RLEnv@27d04ee8203cd5b2f20c3997d13836e5f5b64238`, without patches. All five native input JSONs differ from the GLM arm only at `llm.model`. The model is the pinned documentation's bootstrap example, not an implicit default. OpenRouter, no fallback, 2,048 output tokens, temperature 0.2, 20 turns/1,800 seconds/$5 estimated threshold per repository, refs, date windows, and the approved Docker resource guard were retained. The source/input checkpoint is `a75402fc5aee60b6207c37965359964328024fe2`; the GLM result remains preserved at `c20ba1a095949e330c81921d24ce820792f152d2`.

## Observed outcomes

| Repository | GLM actions / invalid | Sonnet actions / invalid | Sonnet native outcome |
| --- | ---: | ---: | --- |
| scikit-fingerprints | 20 / 11 | 8 / 0 | Saved image, but smoke and fresh-image checks failed with 20 collection errors. Both windows proceeded using that flagged image. Four PRs validated; all rejected with `no_fail_to_pass`. |
| Nipype | 9 / 1 | 7 / 0 | Saved image. Listing 1,000 merged PRs timed out before selection completed or validation started. |
| PsychoPy | 20 / 5 | 20 / 0 | Exhausted turns during Python/dependency setup without saving an image. Second window skipped without another bootstrap. |

The selector's preflight cohort was 16 PRs, including the five comparison inputs. Sonnet reached native selection and validation for four scikit-fingerprints PRs, including two comparison inputs. The six Nipype PRs remain unresolved because of the listing timeout; the six PsychoPy PRs remain unresolved because bootstrap failed. These are not twelve native PR rejections.

| Scikit-fingerprints PR | Parsed tests before / after | F2P / P2P |
| --- | ---: | ---: |
| #545, additional input | 1 / 160 | 0 / 0 |
| #544, comparison input | 1 / 34 | 0 / 0 |
| #542, additional input | 1 / 46 | 0 / 0 |
| #525, comparison input | 8 / 8 | 0 / 8 |

The first three pre-fix results each contain one parsed ERROR. Counts alone do not establish their underlying failure or explain how test identities changed. Upstream discards rejected-stage raw logs, so environment failure, collection/error matching, and task suitability cannot be separated reliably for those cases. PR #525 has eight passing-to-passing tests and no observed failing-to-passing transition.

Nipype's cache records `verify_passed=true` with test exit code 1, which upstream accepts despite test failures. Its subsequent error was a `TimeoutExpired` from `gh pr list --limit 1000 --json ...files`, with a 60-second subprocess limit. Upstream permits three read-only timeout attempts; no manual retry was added. Public PR authentication and smaller GraphQL reads succeeded, but the underlying listing delay is unresolved. This infrastructure failure censors a model comparison of Nipype validation.

PsychoPy initially encountered the project's Python `<3.12` requirement. After a failed `pyenv` build, Sonnet installed Python 3.11.9 with a missing `_lzma` warning, installed the project with `--no-deps`, and began installing test tools. Turn 20 ended with many project dependencies still missing. There was no saved bootstrap or PR validation. This differs from the GLM arm's observed SciPy source-build failure; neither arm established a working environment.

There were 33 BASH actions and two SAVE_SETUP actions. Native transcripts retain 33 entries because successful SAVE_SETUP is omitted. Parsed actions do not imply successful shell commands: several commands pipe output through `tail`, and retained output includes installation failures despite shell exit 0. No external model/Codex repair, additional model probe, manual input retry or solver run occurred. With zero exports, official base/reference grading had no inputs.

## Infrastructure and accounting

The only new runner adaptation was noninteractive `GH_TOKEN` authentication, requested after the user rejected repeated device login. A new dedicated public-read credential was supplied only to the trusted controller. `GITHUB_TOKEN` stayed unset and native `auth.use_gh_cli=false` stayed unchanged. An observed target container had the approved 1.5-CPU/6-GiB limits and neither credential in its environment. The token remains outside Git for subsequent runs; the CI credential was not accessed.

Sonnet attempt 001 was intentionally stopped before authentication and made no native model calls; its original archive and cleanup report are retained separately. Attempt 002 authenticated without browser interaction and completed orchestration. Native command exits were 1, 1, 2 and 1; the fifth window was skipped. Scheduler SUCCEEDED records completion of the controller, while the native outcomes remain the failures above.

Both Sonnet attempts used **3.118936 allocated CPU-hours**, including 0.206054 for the stopped login attempt and 2.912881 for the native controller. All seven issue jobs total **4.625277 CPU-hours**, below the 48-hour ceiling. These are scheduler intervals multiplied by reserved CPUs, including installation, waits and archival, rather than measured CPU utilization. Both Sonnet jobs and all five baseline jobs are terminal; owned container/controller/image cleanup is empty and original archive readback passed.

All native estimated model costs were zero. Actual billed dollars, token usage, request IDs and resolved OpenRouter routing were not retained. The estimated-dollar guard therefore did not provide a billing bound. The comparison does not support a claim that Sonnet or GLM is cheaper per valid task.

## Implications and limits

The native parser accepted Sonnet without modification, supporting a model/format compatibility explanation for the earlier INVALID actions. This is one bounded run per model, not a general reliability estimate. Authentication plumbing and execution date also differ; dependency resolution and upstream bootstrap image tags are not a hermetic environment lock.

Before scaling, the evidence supports investigating bounded PR metadata acquisition, target-test environment readiness, preservation of rejected-stage outputs and test identities, PR selection that yields real F2P transitions, and trustworthy usage/cost accounting. Improved formatting alone did not produce tasks. No upstream fix or production pipeline change is promoted by this experiment.

`evidence/final-outcomes.json` contains the deterministic summary; `evidence/` retains original archives, logs, native caches/transcripts, scheduler accounting and public PR metadata. `summarize.py` recomputes the summary without invoking models or the pipeline. The manifest and verification record establish byte integrity separately from task validity. Source notices in `../licenses/` apply to retained public-code excerpts. No environment image, biological dataset or task release is distributed. Keep this permanent research branch and cited evidence while the conclusion depends on them.
