# Fixed-cohort evidence report

All ten selected repositories remain visible. Missing results are unreported, not zero-cost failures. Only verified archived evidence enters task/success counts. Cost ratios include failed repositories and are withheld until the complete cohort is accounted for.

| Field / repository | Window merges | Native candidates | Paired completed | Exports | Verified tracked | Clean verified oracle | Actual USD | Allocated CPUh | Stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Genomics and genetics / samtools/samtools | 8 | — | 0 | 0 | 0 | 0 | 0.872043 | 1.3986588888888887 | bootstrap_attempt |
| Transcriptomics / scverse/scanpy | 24 | 24 | 3 | 2 | 1 | 0 | 0.559917 | 4.669972222222222 | independent_tracked_test_verification |
| Epigenomics / macs3-project/MACS | 9 | — | 0 | 0 | 0 | 0 | 0.526755 | 2.1325133333333333 | pr_discovery_attempt |
| Proteomics / OpenMS/OpenMS | 217 | — | 0 | 0 | 0 | 0 | 0 | 0.16640555555555553 | source_checkout_attempt |
| Structural biology / lammps/lammps | 34 | — | 0 | 0 | 0 | 0 | 0.938712 | 0.753731111111111 | bootstrap_attempt |
| Metabolomics / matchms/matchms | 11 | — | — | — | — | — | — | — | not_reported |
| Systems biology / opencobra/cobrapy | 4 | — | — | — | — | — | — | — | not_reported |
| Microbiome science / soedinglab/MMseqs2 | 9 | — | — | — | — | — | — | — | not_reported |
| Neuroscience / mne-tools/mne-python | 82 | — | — | — | — | — | — | — | not_reported |
| Bioimage analysis / OHIF/Viewers | 38 | — | — | — | — | — | — | — | not_reported |

Completion proven: False.

Reported actual model cost: $2.897427; reported allocated CPU-hours: 9.12128111111111053.

Verified tasks / successful repositories with archived evidence: 1 / 1.

Full-cohort cost per verified task: —; per successful repository: —.

Window inventory is not a processed-PR denominator. A tracked-test oracle reward of one does not establish whole-command resolution, exact-image replay or release readiness.

## samtools/samtools

Upstream exhausted max_iterations=20 after apt-update timeout and subsequent waits on an apt lock; dependencies were eventually installed but bootstrap never reached SAVE. PR discovery did not run.

Native skip reasons: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## scverse/scanpy

Bootstrap smoke and post-commit checks failed on a Pandas4Warning but upstream continued. PR4329 meets tracked base=0/oracle=1 with ten unchanged untracked Pandas-warning failures; full pytest still exits 1. PR4333 both controls hit VerifierTimeoutError after two 300-second attempts, with no reward.

Native skip reasons: {"empty_source_patch": 1, "no fail-to-pass tests after validation": 1, "no_test_patch": 7, "non_bug_pr": 13}. Controls reached/unstarted: 4/0. Archive accepted: True.

## macs3-project/MACS

Upstream installed MACS3 and saved a flagged bootstrap image after smoke/post-commit tests each hit the original 300-second timeout. Native PR discovery then failed on GitHub GraphQL HTTP 504; no candidate list returned, no PR paired validation or exports. No retry/repair applied.

Native skip reasons: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## OpenMS/OpenMS

The original git checkout of the pinned OpenMS revision exceeded upstream's 60-second subprocess timeout, before any bootstrap model request. Native CLI exited 2; no PR discovery, parser evaluation, export or control was reached. No retry/repair applied.

Native skip reasons: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## lammps/lammps

Upstream exhausted 20 bootstrap BASH turns. Seventeen parsed commands retained trailing </s> or </thinking> tags and produced shell syntax errors; the original sanitizer does not strip them. The saved prompt detected unknown language on ubuntu:24.04. Tools were installed near the end, but no project build/SAVE, PR discovery, exports or controls occurred. No repair/retry applied.

Native skip reasons: {}. Controls reached/unstarted: 0/0. Archive accepted: True.
