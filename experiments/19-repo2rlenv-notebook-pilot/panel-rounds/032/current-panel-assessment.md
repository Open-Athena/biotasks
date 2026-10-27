# Current ten-source development assessment

Checked 27 October 2026. Issue #19 remains incomplete. Latest completed attempts below span development versions; these are not a common-version success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [196](../../panel-rounds/101/result-196.json) | 62.90 | 164 | Generated task omitted a source branch |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [216](../../panel-rounds/108/result-216.json) | 58.74 | 170 | Generated grader omitted a promised HMM statistic comparison; executed probe exposed it; repair allowance exhausted; no native/solver run |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [214](../../panel-rounds/106/result-214.json) | 114.99 | 165 | GLM clarified a public convention; fresh independent validation exhausted the remaining time |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [200](../../panel-rounds/101/result-200.json) | 37.30 | 167 | Wrong submissions rejected; probe/check attribution and public description disagreed |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [206](../../panel-rounds/102/result-206.json) | 20.44 | 45 | Infrastructure failure during session creation; failed operation submitted no command |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [207](../../panel-rounds/102/result-207.json) | 19.78 | 36 | Autonomous source-fidelity rejection: parser skips a real motif observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [208](../../panel-rounds/103/result-208.json) | 14.32 | 41 | Two setup tests failed; final recipe untested; shell-policy violation retained |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../../panel-rounds/101/result-198.json) | 81.59 | 236 | Qualified/published; native reference/empty/solver rewards 1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [211](../../panel-rounds/104/result-211.json) | 8.36 | 27 | Original data URLs returned 404; autonomous input-access rejection without substitution |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [215](../../panel-rounds/108/result-215.json) | 86.33 | 126 | Qualified/published; 19 controls; native reference/empty/solver 1/0/1; no quality repair |

The latest outcomes are two qualified/published tasks, four rejected generated candidates, one source-fidelity rejection, one original-input-access rejection and two infrastructure failures. Rejection of a generated candidate does not establish a broken notebook. Five domains have historical qualified releases across versions. Python only; R remains deferred.

## Current common factory

PyMC 215 and PyHMMER 216 completed on identical 232-file 108 runtime hashes with original notebooks/provenance only. PyMC passed 19 scientific controls and native reference/empty/blind-GLM rewards 1/0/1 without a quality repair. Its public release and forced anonymous empty-cache download are verified. PyHMMER was rejected because an executed HMM-statistic mutation passed a grader that promised to check that field. Its single global repair had already been used for the specification; no extra repair, native execution or solver attempt was launched. All original science/root archives and resource cleanup are verified for both. [Plan](../108/development-panel.json), [PyMC](../108/result-215.json), [PyHMMER](../108/result-216.json), [same runtime](../108/same-runtime-215-216.json).

The full ten-domain common-version assessment remains incomplete; eight original-source cases are planned but unfunded/unfrozen. This one accepted task and one rejected candidate establish those outcomes, not a statistical reliability estimate. The factory changes are general citation feedback, batched evidence reads and earlier solver-time refusal. The previously recorded 114 affected tests and 19 source-admission/proof checks remain separate from these live scientific results.

## Latest qualified release and inspection

[PyMC 215](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-pymc-215/tree/1a27dec5aceb5d0b592fce41b129a996893b89b9) preserves both original analysis branches and all 71 historical count pairs. Native rewards are 1/0/1; 86.33 pipeline minutes and 126 recorded requests exclude bootstrap, archival and publication. Exact source-input comparison and the MIT/BDA3 notice are verified. [Release audit](../../autonomous-runs/215/release-audit.json). Shared model families/stacks and one blind success do not establish universal portability, biological validity or benchmark performance.

The current HTML still displays the earlier qualified MDAnalysis 198 example. Its PyMC replacement is in preparation: the first 97-file selection was preserved outside Git because the two full grid CSV copies should use compact previews and exact published downloads. The notebook can be stored losslessly compressed for display. Do not label the old HTML as the new release.

## Preserved earlier findings

PyMC 213 and Matchms 214 ended with timing infrastructure failures on frozen 105. Their full originals, separate nondispatch proof and fallback archive remain intact. Those failures are not notebook rejections or failed solver answers. Bioframe 207 was rejected for skipping an actual source motif record; Sgkit 211 could not establish access to the original inputs. No operator scientific patch or substituted data was supplied. Detailed original results remain linked from the table and prior revisions.

## Remaining work and budget

Refresh and validate the latest HTML, reconcile eligible closed reservations, then run the remaining eight sources on the identical factory. Preserve source science, complete negative controls and final review; publish only qualified rights-cleared tasks with forced anonymous download. Keep #19 open and PR #23 draft/unmerged; supported promotion requires a fresh branch from main. Never merge the research branch.

$200 authorized / $199 conservative holds / $1 unallocated. Both terminal 215/216 retain their full $5 reservations pending strict accounting; these are not invoices or assumed credits. New campaigns still require a full $5 reservation before launch.

Original two-hour campaign, ten-minute reference/solver, two-minute verifier, two-reference-dispatch and repair limits remain. The proposed three-hour window and reference-dispatch change are unanswered; neither has been adopted. No numerical yield threshold has been assumed.
