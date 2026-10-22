# Fixed-cohort evidence report

All ten selected repositories remain visible. Missing results are unreported, not zero-cost failures. Only verified archived evidence enters task/success counts. Cost ratios include failed repositories and are withheld until the complete cohort is accounted for.

| Field / repository | Window merges | Native candidates | Paired completed | Exports | Verified tracked | Clean verified oracle | Actual USD | Allocated CPUh | Stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Genomics and genetics / samtools/samtools | 8 | — | 0 | 0 | 0 | 0 | 0.872043 | 1.3986588888888887 | bootstrap_attempt |
| Transcriptomics / scverse/scanpy | 24 | 24 | 3 | 2 | 1 | 0 | 0.559917 | 4.669972222222222 | independent_tracked_test_verification |
| Epigenomics / macs3-project/MACS | 9 | — | — | — | — | — | — | — | not_reported |
| Proteomics / OpenMS/OpenMS | 217 | — | — | — | — | — | — | — | not_reported |
| Structural biology / lammps/lammps | 34 | — | — | — | — | — | — | — | not_reported |
| Metabolomics / matchms/matchms | 11 | — | — | — | — | — | — | — | not_reported |
| Systems biology / opencobra/cobrapy | 4 | — | — | — | — | — | — | — | not_reported |
| Microbiome science / soedinglab/MMseqs2 | 9 | — | — | — | — | — | — | — | not_reported |
| Neuroscience / mne-tools/mne-python | 82 | — | — | — | — | — | — | — | not_reported |
| Bioimage analysis / OHIF/Viewers | 38 | — | — | — | — | — | — | — | not_reported |

Completion proven: False.

Reported actual model cost: $1.431960; reported allocated CPU-hours: 6.0686311111111107.

Verified tasks / successful repositories with archived evidence: 1 / 1.

Full-cohort cost per verified task: —; per successful repository: —.

Window inventory is not a processed-PR denominator. A tracked-test oracle reward of one does not establish whole-command resolution, exact-image replay or release readiness.

## samtools/samtools

Upstream exhausted max_iterations=20 after apt-update timeout and subsequent waits on an apt lock; dependencies were eventually installed but bootstrap never reached SAVE. PR discovery did not run.

Native skip reasons: {}. Controls reached/unstarted: 0/0. Archive accepted: True.

## scverse/scanpy

Bootstrap smoke and post-commit checks failed on a Pandas4Warning but upstream continued. PR4329 meets tracked base=0/oracle=1 with ten unchanged untracked Pandas-warning failures; full pytest still exits 1. PR4333 both controls hit VerifierTimeoutError after two 300-second attempts, with no reward.

Native skip reasons: {"empty_source_patch": 1, "no fail-to-pass tests after validation": 1, "no_test_patch": 7, "non_bug_pr": 13}. Controls reached/unstarted: 4/0. Archive accepted: True.
