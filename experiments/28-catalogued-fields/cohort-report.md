# Fixed-cohort evidence report

All ten selected repositories remain visible. Missing results are unreported, not zero-cost failures. Only verified archived evidence enters task/success counts. Cost ratios include failed repositories and are withheld until the complete cohort is accounted for.

| Field / repository | Window merges | Native returned | Entered | Paired started/completed | Exports | Verified tracked | Clean verified oracle | Actual USD | Allocated CPUh | Stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Genomics and genetics / samtools/samtools | 8 | — | 0 | 0/0 | 0 | 0 | 0 | 0.872043 | 1.399 | bootstrap_attempt |
| Transcriptomics / scverse/scanpy | 24 | 24 | 24 | 3/3 | 2 | 1 | 0 | 0.559917 | 4.670 | independent_tracked_test_verification |
| Epigenomics / macs3-project/MACS | 9 | — | 0 | 0/0 | 0 | 0 | 0 | 0.526755 | 2.133 | pr_discovery_attempt |
| Proteomics / OpenMS/OpenMS | 217 | — | 0 | 0/0 | 0 | 0 | 0 | 0.000000 | 0.166 | source_checkout_attempt |
| Structural biology / lammps/lammps | 34 | — | 0 | 0/0 | 0 | 0 | 0 | 0.938712 | 0.754 | bootstrap_attempt |
| Metabolomics / matchms/matchms | 11 | 11 | 4 | 2/1 | 0 | 0 | 0 | 0.133545 | 0.769 | paired_pr_validation_partial |
| Systems biology / opencobra/cobrapy | 4 | 4 | 4 | 0/0 | 0 | 0 | 0 | 0.332655 | 1.027 | native_candidate_filtering |
| Microbiome science / soedinglab/MMseqs2 | 9 | — | 0 | 0/0 | 0 | 0 | 0 | 0.960333 | 1.906 | bootstrap_attempt |
| Neuroscience / mne-tools/mne-python | 82 | — | — | —/— | — | — | — | — | — | not_reported |
| Bioimage analysis / OHIF/Viewers | 38 | — | — | —/— | — | — | — | — | — | not_reported |

Cohort result evidence complete: False.

Final live resource/process checks, scientific audit, issue conclusion/readback/closure and task-owned temporary cleanup are separate requirements.

Reported actual model cost: $4.323960; reported allocated CPU-hours: 12.823019.

Verified tasks / successful repositories with archived evidence: 1 / 1.

Full-cohort cost per verified task: —; per successful repository: —.

Window inventory is not a processed-PR denominator. A tracked-test oracle reward of one does not establish whole-command resolution, exact-image replay or release readiness.

## samtools/samtools

Upstream exhausted max_iterations=20 after apt-update timeout and subsequent waits on an apt lock; dependencies were eventually installed but bootstrap never reached SAVE. PR discovery did not run.

Native skip reasons: {}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## scverse/scanpy

Bootstrap smoke and post-commit checks failed on a Pandas4Warning but upstream continued. PR4329 meets tracked base=0/oracle=1 with ten unchanged untracked Pandas-warning failures; full pytest still exits 1. PR4333 both controls hit VerifierTimeoutError after two 300-second attempts, with no reward.

Native skip reasons: {"empty_source_patch": 1, "no fail-to-pass tests after validation": 1, "no_test_patch": 7, "non_bug_pr": 13}. Native decision errors: {}. Controls reached/unstarted: 4/0. Archive accepted: True.

## macs3-project/MACS

Upstream installed MACS3 and saved a flagged bootstrap image after smoke/post-commit tests each hit the original 300-second timeout. Native PR discovery then failed on GitHub GraphQL HTTP 504; no candidate list returned, no PR paired validation or exports. No retry/repair applied.

Native skip reasons: {}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## OpenMS/OpenMS

The original git checkout of the pinned OpenMS revision exceeded upstream's 60-second subprocess timeout, before any bootstrap model request. Native CLI exited 2; no PR discovery, parser evaluation, export or control was reached. No retry/repair applied.

Native skip reasons: {}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## lammps/lammps

Upstream exhausted 20 bootstrap BASH turns. Seventeen parsed commands retained trailing </s> or </thinking> tags and produced shell syntax errors; the original sanitizer does not strip them. The saved prompt detected unknown language on ubuntu:24.04. Tools were installed near the end, but no project build/SAVE, PR discovery, exports or controls occurred. No repair/retry applied.

Native skip reasons: {}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## matchms/matchms

Bootstrap smoke and fresh-image checks passed at the pinned newer repo revision. Native returned 11 PRs but entered four: PR966 had missing chemap in both collection stages, two candidates were filtered, then PR958 post-fix Docker exec raised OSError errno 7 on an oversized inline patch script. Two pairs started, one completed, no exports; seven returned PRs were never entered. No repair/retry applied.

Native skip reasons: {"no fail-to-pass tests after validation": 1, "no_new_test_funcs": 1, "no_test_patch": 1}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## opencobra/cobrapy

All four returned window PRs were entered and filtered before paired validation: three no_test_patch and one no_new_test_funcs (PR1492). The saved bootstrap image was independently flagged because both original 300-second smoke checks timed out, but those timeouts did not cause this zero-export outcome. No API/validation exception, repair or retry.

Native skip reasons: {"no_new_test_funcs": 1, "no_test_patch": 3}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## soedinglab/MMseqs2

The official agent installed CMake/compiler/Rust dependencies and reached compilation, then exhausted 20 turns (19 BASH, one INVALID) without SAVE_SETUP. Two build commands and a later file-inspection command timed out at the original 300-second limit; upstream also explicitly started background make. No PR discovery, parser evaluation, export or control occurred. Actual compiler/OOM causality unmeasured; no repair/retry or resource change.

Native skip reasons: {}. Native decision errors: {}. Controls reached/unstarted: 0/0. Archive accepted: True.
