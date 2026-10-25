# Current ten-source development assessment

Latest completed scientific outcome per source. Infrastructure failures are recorded separately. These development versions differ; this is not a common-version holdout or success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [177](../../panel-rounds/081/result-177.json) | 15.36 | 49 | Specification rejected: proposed probe contradicts normalization |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [178](../../panel-rounds/082/result-178.json) | 15.29 | 60 | Specification rejected: unsupported defaults/metadata claims |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [179](../../panel-rounds/083/result-179.json) | 25.19 | 77 | Specification rejected: unsupported writer/population claim |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [176](../../panel-rounds/080/result-176.json) | 37.00 | 119 | Qualified, published and download verified |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [168](../../panel-rounds/069/result-168.json) | 82.79 | 133 | Candidate rejected: unresolved independent comparison |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [169](../../panel-rounds/071/result-169.json) | 21.21 | 50 | Specification stopped: source population-loss concern |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [181](../../panel-rounds/085/result-181.json) | 8.47 | 38 | Setup rejected: style/dependency tests exhausted |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [182](../../panel-rounds/086/result-182.json) | 38.06 | 138 | Grading rejected: retained answer fixture and probe evidence |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [142](../../panel-rounds/026/result-142.json) | 109.15 | 180 | Candidate rejected; see original records |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [145](../../panel-rounds/029/result-145.json) | 77.02 | 139 | Qualified, published and download verified |

**Two latest selected outcomes are published and eight are generated-candidate rejections.** Earlier qualified releases exist for four domains: PyMC 145, PyHMMER 161, Matchms 171 and NeuroKit 176. A later rejected candidate does not invalidate an earlier qualified release or show that the source is broken. Pyteomics 139remains native-complete under its original redistribution hold. [Machine-readable evidence](current-panel-summary.json).

The latest qualified viewer/release remains NeuroKit 176: 21 scientific controls, native reference/empty/blind-GLM 1/0/1 without exceptions, exact published bundle and forced anonymous download verification. The current viewer must not be replaced by an unqualified task or pair later prompts with old outputs. [Release audit](../../autonomous-runs/176/release-audit.json).

## Current frozen continuation

The unchanged 221-file runtime has terminal specification rejections 177/178/179, setup rejection 181, grading rejection 182 and native-preparation infrastructure failure 180. Scanpy 180passed 13 final pre-Harbor controls/review before the fixed 30-second unpack limit stopped native preparation; no Harbor/native control or solver launched. Complete 2414 science/71 root files and fresh four-SDK-owner absence are verified, with source-bound native non-dispatch. [Original failure](../084/failure-180.md).

MDAnalysis 182passed 16 controls, but review found an installed answer fixture for a recovered endpoint and inaccurate probe evidence quotes. Setup had assessed only the initial three exports; construction recovered two more endpoints. The already-consumed global quality repair was not replenished. Complete 2144 science/73 root files and fresh four-owner absence are verified. [Rejection](../086/rejection-182.md), [independent original-source/reference comparison](../086/fixture-corroboration-182.json).

Sgkit 183 is submitted with its full $5 reservation; PyMC 184 remains unfunded. Both explicitly select the original public runtime with an empty reviewed delta. The newer tool-feedback and preparation-deadline candidates do not silently enter this round. Bioframe 175and NeuroKit 176used the earlier 219-file runtime;175 retains its original upload 502 failure. No common-version ten-case result exists yet. R remains deferred. [Source plan](../081/development-panel.json).

## General changes and remaining evidence

The identical-file upload recovery passes 358 affected offline checks and three real-provider synthetic-fault controls; current qualified scientific adoption is still unproven. It does not retry models/commands/jobs. [Evidence](../../factory-checks/upload-retry/README.md).

Specific malformed-artifact feedback passes 275 offline checks and remains unproven in a fresh live run. The next native-preparation patch passes 6 runner and 12 strict non-dispatch checks without extending the trial deadline; live adoption remains pending. [Argument feedback](../../factory-checks/artifact-argument-feedback/README.md), [preparation deadline](../../factory-checks/native-preparation-deadline/README.md).

Two scientific workflow changes remain under consideration: keep speculative executable-comparison/probe mechanics out of the initial specification; assess answer-bearing dependencies against the final endpoint inventory before freezing the task. Neither is an adopted scientific prompt/contract change. Source coverage, methods, populations, deterministic controls and native qualification remain required. No manual task repair is permitted.

All current campaign hosts are terminal and actual owned SDK sandboxes are independently absent. The aggregate authorization is$200 counting the extra $100 once, fully conservatively reserved including the new full $5 reservation for 183;184 has no funding. Reservations are not invoices/credits. Keep issue 19 open and PR 23 draft/unmerged; never merge the research branch. [Ledger](../../aggregate-budget.json), [completion audit](completion-audit.md).
