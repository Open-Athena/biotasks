# Current ten-source development assessment

Latest completed attempt per source across development versions, including infrastructure outcomes. This is not a common-version holdout or success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [196](../101/result-196.json) | 62.90 | 164 | Generated task omitted a source branch |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [199](../101/result-199.json) | 80.49 | 281 | Infrastructure failure after idle sandbox deletion; no accepted final review |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [195](../100/result-195.json) | 92.20 | 238 | Qualified/published; blind solver timed out with reward0 |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [200](../101/result-200.json) | 37.30 | 167 | Wrong submissions rejected; probe/check attribution and public description disagreed |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [206](../102/result-206.json) | 20.44 | 45 | Infrastructure failure during session creation; failed operation submitted no command |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [207](../102/result-207.json) | 19.78 | 36 | Autonomous source-fidelity rejection: parser skips a real motif observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [193](../098/result-193.json) | 8.70 | 36 | Generated setup exhausted two reference tests |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../101/result-198.json) | 81.59 | 236 | Qualified/published; native reference/empty/solver rewards1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [194](../099/result-194.json) | 39.76 | 91 | Setup budget/restoration infrastructure failure |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [197](../101/result-197.json) | 114.90 | 223 | Final grading review timed out |

Latest across versions: **two validated/published, three generated-candidate rejections, one source-fidelity rejection and four infrastructure failures**. Five domains have published releases across history. A rejected generated task does not establish a broken source. Python only; R deferred.

## Current versions

The common 232-file baseline completed five cases: 196/200 generated-task rejections, 197/199 infrastructure failures and qualified/published MDAnalysis 198. The lifecycle-only successor completed206 with a session-creation infrastructure failure and207 with an independently detected source-fidelity rejection. Original archives/root exports and direct original-ID/owner cleanup are verified. Bioframe executed successfully and replayed identically twice; repeatability alone did not establish scientific correctness. No previous scientific outcome is relabelled.

The [next version](../103/development-panel.json) additionally reconciles a late-visible empty session on the sole creation retry, retaining exactly one execute request and the original deadline.182 affected tests, eight source-admission/refusal tests and three real-provider controls pass. Scientific prompts, model/resource/time/repair bounds are unchanged.208 Pyteomics is submitted;209 Sgkit and210 Matchms remain unfunded. No new scientific qualification follows from the infrastructure controls. [Checks](../../factory-checks/session-create-conflict/README.md).

Latest qualified release remains [MDAnalysis 198](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-mdanalysis-rmsd/tree/166d99e941b7e154fc6360f48e739bd19127cfb2): five source analyses, 19 controls, native 1/0/1, full originals/cleanup and forced anonymous download verified. Its matching latest explorer remains published and browser/public-readback verified. [Audit](../../autonomous-runs/198/release-audit.json).

## Pending work and budget

Review-feedback and coverage-handoff improvements remain candidates. Initial probe authoring deliberately remains blind to grader results; simply returning the hidden grader report would weaken that boundary. A possible separation of executed checker attribution from scientific negative coverage is still under consideration, not adopted. No scientific gate or reward is relaxed. Pyteomics and Sgkit redistribution remain unestablished.

**$200 authorized / $196.25 conservative holds / $3.75 unallocated**, including the full $5for 208 and $1for completed infrastructure compatibility. The unchanged auditor released only $7 for 206/207 stages never dispatched; all used-stage holds remain.199still retains its full $5. These are exposure reservations, not invoices or assumed credits. [Ledger](../../aggregate-budget.json).

Keep #19 open and PR #23 draft/unmerged. Complete the diverse-source assessment and validate general improvements on fresh source-only inputs; publish only qualified, rights-cleared replacements. No manual scientific edits, notebook-specific factory fixes or research-branch merge.
