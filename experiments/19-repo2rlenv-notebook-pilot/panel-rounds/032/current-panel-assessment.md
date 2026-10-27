# Current ten-source development assessment

Latest completed attempt per source across development versions, including infrastructure outcomes. This is not a common-version holdout or success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [196](../101/result-196.json) | 62.90 | 164 | Generated task omitted a source branch |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [199](../101/result-199.json) | 80.49 | 281 | Grader repair interrupted by deleted idle sandbox; no accepted final review |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [195](../100/result-195.json) | 92.20 | 238 | Qualified/published; blind solver timed out with reward 0 |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [200](../101/result-200.json) | 37.30 | 167 | Wrong submissions rejected, but probe/check attribution and public description disagreed |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [191](../096/result-191.json) | 85.11 | 214 | Generated check/probe attribution disagreed |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [192](../097/result-192.json) | 42.93 | 82 | Source parser discards a real observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [193](../098/result-193.json) | 8.70 | 36 | Generated setup exhausted two tests |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../101/result-198.json) | 81.59 | 236 | Qualified/published; native reference/empty/solver rewards 1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [194](../099/result-194.json) | 39.76 | 91 | Setup budget/restoration infrastructure failure |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [197](../101/result-197.json) | 114.90 | 223 | Final grading review timed out |

Latest across versions: **two validated/published, four generated-candidate rejections, one source-fidelity rejection and three infrastructure failures**. Five domains have published releases across history. A rejected generated task does not establish a broken source. Python only; R deferred.

## Frozen scientific round and lifecycle continuation

The 232-file baseline has five completed cases: 196/200 generated-task rejections, 197/199 infrastructure failures and qualified/published MDAnalysis 198. All originals/root exports and SDK-ID/owner cleanup are verified. No old outcomes are relabeled as the new candidate. [Baseline panel](../101/development-panel.json).

The next five original sources are planned under an explicitly new lifecycle-only version. It disables authoring idle stop while keeping the positive absolute TTL, resources, deadlines and cleanup. Every scientific prompt and all other executable behavior are identical. Offline setup/session and admission checks pass; no live idle-survival or new scientific qualification is claimed yet. Never-submitted Scanpy 201 funding transfers to 206 without additional reservation. [Continuation](../102/development-panel.json), [checks](../../factory-checks/author-idle-lifecycle/offline-checks.json).

Latest qualified release remains [MDAnalysis 198](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-mdanalysis-rmsd/tree/166d99e941b7e154fc6360f48e739bd19127cfb2): 19 controls, native 1/0/1, full originals/cleanup and forced anonymous download verified. Its matching latest explorer is published and browser/public-readback verified. [Audit](../../autonomous-runs/198/release-audit.json), [HTML readback](../../autonomous-runs/198/explorer-public-readback.json).

## Pending general feedback and budget

The review-feedback candidate identifies malformed nested JSON and missing/unexpected/duplicate hint IDs without filling assessments. The coverage handoff finding separates export availability from scientific eligibility. Another candidate is to give the initial probe author actual executed grading feedback before freezing its expected failing-check subset; that is still being considered, not implemented. No scientific gate or reward is relaxed. Pyteomics and Sgkit redistribution remain unestablished.

**$200 authorized / $196.25 conservatively held / $3.75 unallocated**, including the transferred full $5 Scanpy reservation. No invoice or credits inferred. Completed 199/200 remain fully held pending their separate reconciliation. [Ledger](../../aggregate-budget.json), [funding transfer](../102/funding-206.json).

Keep #19 open and PR #23 draft/unmerged. Complete the diverse-source assessment and validate general improvements on fresh source-only inputs; publish only qualified, rights-cleared replacements. No manual scientific edits, notebook-specific factory fixes or research-branch merge.
