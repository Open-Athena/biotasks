# Current ten-source development assessment

Checked 27 October 2026. Issue #19 remains incomplete. Latest completed attempts below span development versions; these are not a common-version success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [217](../../panel-rounds/108/result-217.json) | 15.12 | 51 | Reference succeeded; final specification review alleged an ordering defect contradicted by explicit set identity; generated-review rejection under audit |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [216](../../panel-rounds/108/result-216.json) | 58.74 | 170 | Generated grader omitted a promised HMM statistic comparison; executed probe exposed it; repair allowance exhausted; no native/solver run |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [218](../../panel-rounds/108/result-218.json) | 39.89 | 104 | Reference/replay passed; repaired specification introduced unsupported input companions and was rejected before construction |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [219](../../panel-rounds/108/result-219.json) | 40.12 | 149 | Required valid CSV representation rejected;14/15control expectations met; final review stopped the generated grader; no native/solver run |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [220](../../panel-rounds/108/result-220.json) | 114.26 | 211 | Public-question repair completed; fresh grading exhausted operation admission; no native/solver trial; exact embedding/label target concern remains |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [207](../../panel-rounds/102/result-207.json) | 19.78 | 36 | Autonomous source-fidelity rejection: parser skips a real motif observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [208](../../panel-rounds/103/result-208.json) | 14.32 | 41 | Two setup tests failed; final recipe untested; shell-policy violation retained |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../../panel-rounds/101/result-198.json) | 81.59 | 236 | Qualified/published; native reference/empty/solver rewards 1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [211](../../panel-rounds/104/result-211.json) | 8.36 | 27 | Original data URLs returned 404; autonomous input-access rejection without substitution |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [215](../../panel-rounds/108/result-215.json) | 86.33 | 126 | Qualified/published; 19 controls; native reference/empty/solver 1/0/1; no quality repair |

The latest outcomes are two qualified/published tasks, four rejected generated candidates, one generated-review rejection under audit, one source-fidelity rejection, one original-input-access rejection and one infrastructure failure. Rejection of a generated candidate does not establish a broken notebook. Five domains have historical qualified releases across versions. Python only; R remains deferred.

## Current common factory

Six cases (215–220) completed with identical 232-file runtime hashes, original notebook/provenance inputs only, and zero operator scientific edits. All six original reference workflows and clean replays ran successfully. Their generated-task outcomes are one qualified public release, three rejected candidates, one review rejection under audit and one infrastructure failure:

- PyMC passed 19 controls and native reference/empty/blind-GLM rewards 1/0/1; publication and forced anonymous download are verified.
- PyHMMER's grader omitted a promised statistic comparison. An executed negative probe exposed it.
- COBRApy's final review alleged an ordering ambiguity contradicted by the public contract.
- Matchms's repair restored an omitted cosine-analysis branch but introduced unverified input companions.
- NeuroKit's grader rejected a valid trailing-blank-line CSV representation. Fourteen of fifteen control expectations were met, so final review stopped it.
- Scanpy initially met all 16 executed control expectations, but review identified missing Gene Expression input context, incomplete comparison coverage and a missing scientific negative. GLM used the existing single repair to correct the public question and grader proposal. Fresh grading could not admit another full operation under the remaining worker clock; repaired controls, native trials and solver are absent. This was not a ten-minute scientific computation timeout.

A separate read-only audit flags Scanpy's near-exact embedding coordinates and arbitrary cluster-label arrays as unresolved scientific targets: same-stack byte-identical recomputation does not establish the scientific equivalence claim. No manual task fix, reward or acceptance override was supplied. This concern is distinct from the recorded infrastructure stop.

Complete original science/root exports and fresh cleanup are verified for all six. Scanpy uses its original quiescent fallback snapshot; its absent regular seal was not reconstructed. These outcomes do not establish broken notebooks. One accepted task from six development cases does not establish reliability on new notebooks. [Plan](../108/development-panel.json), [Scanpy](../108/result-220.json).

Bioframe 221 has its full funding reservation and frozen original inputs but is not submitted; Pyteomics, MDAnalysis and Sgkit remain unfunded/unfrozen. No worker code, prompt or repair allowance was changed for the observed failures. [Identical-runtime proof, including frozen 221](../108/same-runtime-215-through-221.json).

## Latest qualified release and inspection

[PyMC 215](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-pymc-215/tree/1a27dec5aceb5d0b592fce41b129a996893b89b9) preserves both source analyses and all 71 historical count pairs. It took 86.33 pipeline minutes and 126 recorded requests, excluding bootstrap, archival and publication. Source-input identity and notices are verified. [Release audit](../../autonomous-runs/215/release-audit.json).

The latest HTML displays this release, with 13 actual pipeline stages and 13 solver steps, captured prompts/inputs/outputs, notebook rendering and exact downloads. Browser navigation, mobile layout, text contrast and public Git readback passed. Shared model families/stacks and one blind success do not establish universal portability, biological validity or benchmark performance.

## Preserved earlier findings

The table above reports the latest completed case per domain across development versions. Five domains have historical qualified releases. Mixed-version results are not a common-version success rate. Earlier failures and releases remain available through their original records and prior revisions. In particular, Bioframe 207 lost a real motif record in the original parser; Sgkit 211 could not access original data URLs. No operator scientific patch or substitute data was supplied.

## Remaining work and budget

Complete the four remaining sources on the unchanged factory. Then assess shared failure patterns, including repair drift, grader implementation errors and review reliability. Publish only qualified, rights-cleared tasks with verified downloads. Keep #19 open and PR #23 draft/unmerged; supported promotion requires sufficient evidence and a fresh branch from main. Never merge the research branch.

$200 is authorized; $196.75 is held conservatively and $3.25 is unallocated, including a full $5 reservation for Bioframe 221. Closed 220 retains $1 after all five full SDK lifetimes, 300 seconds at each end, margin and upward quarter-dollar rounding. A new campaign still requires a full $5 reservation. These are not invoices or assumed credits. [Ledger](../../aggregate-budget.json), [220 audit](../108/closed-220-applied.json).

Original model, resource, two-hour campaign, ten-minute reference/solver, two-minute verifier, two-reference-dispatch and repair limits remain. The proposed three-hour window and reference-dispatch change are unanswered; neither has been adopted. No numerical yield threshold has been assumed.
