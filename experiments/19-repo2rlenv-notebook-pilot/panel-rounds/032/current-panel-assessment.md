# Current ten-source development assessment

Latest completed attempt per source across development versions, including infrastructure outcomes. This is not a common-version holdout or success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [196](../101/result-196.json) | 62.90 | 164 | Generated task omitted a distinct source branch; check/probe attribution disagreed |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [188](../093/result-188.json) | 12.38 | 58 | Generated method description still unsupported |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [195](../100/result-195.json) | 92.20 | 238 | Qualified, published; blind solver timed out with reward0 |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [190](../095/result-190.json) | 7.06 | 34 | Generated offline input setup exhausted two tests |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [191](../096/result-191.json) | 85.11 | 214 | Generated check description/probe attribution disagreed |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [192](../097/result-192.json) | 42.93 | 82 | Source parser discards a real observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [193](../098/result-193.json) | 8.70 | 36 | Generated setup exhausted two tests |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../101/result-198.json) | 81.59 | 236 | Qualified and published; native oracle/no-op/solver rewards 1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [194](../099/result-194.json) | 39.76 | 91 | Setup controller budget/restoration infrastructure failure |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [197](../101/result-197.json) | 114.90 | 223 | Final grading review timed out; original fallback snapshot and cleanup verified |

**Latest attempts across versions: two validated/published tasks, five generated-candidate rejections, one source-fidelity rejection and two infrastructure failures.** Five domains have published releases across history. An invalid generated task does not establish that its source notebook is broken. R remains deferred.

## Current common-version round

All ten original source-only inputs are frozen against the same 232-file scientific version. Three cases have completed: COBRApy 196 rejected an incomplete generated task, PyMC 197 timed out during final review, and **MDAnalysis 198 qualified and was published**. PyHMMER 199 and NeuroKit 200 are running. The other five are frozen but unfunded/unsubmitted. No previous task, answer, staging recipe or fixture-removal hint is supplied. [Panel](../101/development-panel.json).

MDAnalysis passed 19 final controls after one GLM grader repair and native oracle/no-op/solver rewards **1/0/1**. All three original simulation/structure inputs match the separately reviewed unmodified test-data identities. The task preserves five source analyses, with no operator scientific edit. The original archive has 2,893 files / 256,050,864 bytes plus 106 root-export files. Four SDK creation IDs and all seven owner labels were freshly checked; native supervisors may already have no IDs after successful Harbor cleanup, and that limitation is explicit rather than reconstructed. [Result](../101/result-198.json), [scientific release gate](../../autonomous-runs/198/scientific-release-check.json), [cleanup](../../autonomous-runs/198/provider-cleanup.json).

The exact native bundle b90d043a was published at immutable HF revision166d99e9, then every release file/mode and bundle identity passed a forced anonymous empty-cache download. Pipeline time was **81.59 minutes / 236 requests**, excluding bootstrap, export/readback and publication. [Release](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-mdanalysis-rmsd/tree/166d99e941b7e154fc6360f48e739bd19127cfb2), [download verification](../../autonomous-runs/198/hub-download-verification.json), [timing](../101/performance-198-detail.json).

One qualified example in this common-version round does not establish cross-domain reliability. The rejected COBRApy task omitted an eligible source branch; PyMC passed 18 controls but never obtained valid final review. Their original failures remain unchanged. [196](../101/result-196.json), [197](../101/result-197.json).

## Previous fixed round and retained qualified examples

The prior 224-file round remains 10/10 terminal: seven generated-candidate rejections, one source-fidelity rejection, two infrastructure failures, zero qualified tasks. Original archives and cleanup are audited. [Fixed-round results](../090/fixed-round-outcomes.json), [integrity audit](../090/round-integrity-audit.json). Matchms 195 used a later 229-file version; it retains its published 19-control result and native1/0/0 with a handled solver timeout. [195 audit](../../autonomous-runs/195/release-audit.json).

## Pending general changes and execution budget

The [review-feedback candidate](../../factory-checks/review-feedback/README.md) names missing/unexpected/duplicate hint IDs and clarifies actual nested JSON. Five offline tests preserve old/new acceptance across 1,080 scenarios. The [coverage handoff finding](../101/coverage-handoff-findings.md) distinguishes export availability from scientific eligibility. Neither is applied to this frozen round. Source-preservation guidance and the setup-budget boundary are integrated; live adoption of the additional owning-worker construction-repair route remains unproved. Pyteomics and Sgkit redistribution remain unestablished.

**$200 authorized / $199.25 conservatively held / $0.75 unallocated.** The original strict197cleanup-cost refusal is retained. A separate conservative bound prices the unrecorded grading-deletion interval through later exact-ID absence, adds the existing margin/rounding, and retains $1.25. That releases $3.75 and funds NeuroKit200’s full $5 reservation. Original receipts and clocks are unchanged; no invoices or credits are inferred. [Applied bound](../101/closed-197-late-absence-applied.json), [162 checks](../101/late-absence-cost-checks.json), [funding200](../101/funding-200.json), [ledger](../../aggregate-budget.json).

Keep #19 open and PR #23 draft/unmerged. Finish the diverse round, assess aggregate failures, validate general changes on fresh source-only campaigns and publish only qualified replacements. Do not narrow source science, hand-edit generated tasks, replenish bounded repairs or merge the research branch.
