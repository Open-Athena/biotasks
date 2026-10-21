# Additional biology cohort

## 2026-10-21 — scope and inputs

The user requested more biology repositories with the same official pipeline/settings and no extra repairs. Issue #27 records the new cohort; #25/#26 remain preserved separately. Started from main 2a1950d239f1ada467c35393991dac87debe35f7. Chose Biopython, scikit-bio and AnnData to cover general sequence biology, biological algorithms and annotated biological matrices. This is a selected cohort, not representative sampling.

Pinned each current default-branch commit. The same September window contains 11/39/28 merged PRs, fully covered by the newest-300 preflight. Upstream controls all filtering/validation/export; no per-PR handpicking. Preserve the same model/provider, fallback, 20-turn/1800-second bootstrap and $5 estimated threshold per repository. Actual billing is unavailable unless upstream emits it; zero estimates are not free-use evidence.

Reuse the adapter at 6e3c0afb, including its cleanup correction. Infrastructure-only differences are one-config payload selection, experiment resource names, creation of the empty published archive directory, a preflight refusing existing upstream bootstrap tags, and a 90-minute complete job cap per repo (24 allocated CPU-hour total ceiling). No source, prompt, installer recipe or grading change. Each repo has a separate fresh controller/cache; jobs are serial and no failure is repaired or retried. Native exports remain local-image dependent; publication is outside scope.

No model, build or test run for this cohort has launched yet. Configuration/runner checkpoint and syntax/adapter fixture checks precede submission.
