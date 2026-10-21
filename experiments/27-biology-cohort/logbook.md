# Additional biology cohort

## 2026-10-21 — scope and inputs

The user requested more biology repositories with the same official pipeline/settings and no extra repairs. Issue #27 records the new cohort; #25/#26 remain preserved separately. Started from main 2a1950d239f1ada467c35393991dac87debe35f7. Chose Biopython, scikit-bio and AnnData to cover general sequence biology, biological algorithms and annotated biological matrices. This is a selected cohort, not representative sampling.

Pinned each current default-branch commit. The same September window contains 11/39/28 merged PRs, fully covered by the newest-300 preflight. Upstream controls all filtering/validation/export; no per-PR handpicking. Preserve the same model/provider, fallback, 20-turn/1800-second bootstrap and $5 estimated threshold per repository. Actual billing is unavailable unless upstream emits it; zero estimates are not free-use evidence.

Reuse the adapter at 6e3c0afb, including its cleanup correction. Infrastructure-only differences are one-config payload selection, experiment resource names, creation of the empty published archive directory, a preflight refusing existing upstream bootstrap tags, and a 90-minute complete job cap per repo (24 allocated CPU-hour total ceiling). No source, prompt, installer recipe or grading change. Each repo has a separate fresh controller/cache; jobs are serial and no failure is repaired or retried. Native exports remain local-image dependent; publication is outside scope.

No model, build or test run for this cohort has launched yet. Configuration/runner checkpoint and syntax/adapter fixture checks precede submission.

## 2026-10-21 — Biopython completed, no exports

The first job reached a seven-turn SAVE_SETUP but smoke and fresh-image checks both failed: pytest collection exit 2, nine collection errors, missing external dependencies. Some model BASH inputs appended fabricated Output text, producing shell exit 127; preserve transcript rather than cleaning it. Upstream cached the flagged image and continued. The first pre-fix validation was PR #5337 (base 0d51cefb25dd); native CLI aborted with OSError errno 7, argument list too long: docker. Native exit code 2 is a failure despite the outer infrastructure job/phase ending normally. No PR validation completed and no task was exported; the other window PRs were not fully processed.

Read-only diagnosis matched the first PR's base and measured its public diff: 218062 bytes total, 205169 bytes in test-file diffs. Pinned DockerSandbox.exec passes the whole shell command as one argument; pinned validation embeds test patches in that command. This is consistent with the execution argument-size limit. No command transport change, missing-dependency repair, PR skip or retry was made. The source/size evidence is in inspection/biopython-large-patch.json. This is separate from the bootstrap's failed collection.

Iris archive readback SHA passed and all owned containers, images and volumes were empty. Reviewed bootstrap records and native logs are retained in evidence/biopython-001. Scikit-bio started automatically after cleanup verification, with a separate fresh cache and unchanged settings.
