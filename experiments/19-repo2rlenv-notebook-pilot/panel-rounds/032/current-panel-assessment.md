# Current ten-source development assessment

Latest independently archived completed outcome per source. These are development versions, not a common-version holdout or a success-rate estimate. Original failures and superseded runs remain preserved. Active source-only repeat152 is excluded from these completed-outcome counts.

| Domain | Source | Campaign | Pipeline minutes | Accounted model requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [133](../../panel-rounds/026/result-133.json) | 37.30 | 110 | Native controls complete; qualification held |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [134](../../panel-rounds/026/result-134.json) | 54.17 | 154 | Generated candidate rejected |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [147](../../panel-rounds/030/result-147.json) | 111.96 | 169 | Qualified, published and download verified |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [136](../../panel-rounds/026/result-136.json) | 4.48 | 25 | Generated candidate rejected |
| Single-cell transcriptomics | [scverse/scanpy](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [150](../../panel-rounds/033/result-150.json) | 105.81 | 166 | Native controls complete; qualification held |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [138](../../panel-rounds/026/result-138.json) | 39.14 | 102 | Native controls complete; qualification held |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [139](../../panel-rounds/026/result-139.json) | 40.82 | 122 | Native controls complete; qualification held |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [151](../../panel-rounds/034/result-151.json) | 70.70 | 149 | Native controls complete; qualification held |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [142](../../panel-rounds/026/result-142.json) | 109.15 | 180 | Generated candidate rejected |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [145](../../panel-rounds/029/result-145.json) | 77.02 | 139 | Qualified, published and download verified |

**Two tasks are qualified/published, five have qualification holds, and three generated candidates were rejected.** Seven completed native-control sets are distinct from publication qualification. Earlier qualified examples, including PyHMMER124, are retained separately rather than substituted for latest outcomes.

[Scanpy150](../033/qualification-150.md) passed 21 final controls and native reference/empty/GLM rewards 1/0/1 in 105.81 minutes, but its exact cluster-label and componentwise embedding contract remains unsupported. The solver recorded `AgentTimeoutError`; its retained reward is not an exception-free completion. No manual task changes or publication followed.

[MDAnalysis151](../034/qualification-151.md) passed 17 final controls and native rewards 1/0/1 in 70.70 minutes. GLM removed one answer-bearing test module, but another retained module still contains a matching requested RMSD. It remains held. The complete archives, original host records and fresh seven-owner absence are verified for both runs. Neither hold means the notebook source is broken.

Measured pipeline times across the ten latest outcomes are **4.48–111.96 minutes**; the seven completing native controls took **37.30–111.96 minutes**. These exclude bootstrap, archive verification and publication. Short failures do not estimate successful throughput.

Later general prompt changes require scientific equivalence before reference matching and reassessment of answer isolation against the final recovered endpoint set. Those changes were not in150/151. The required review gate passed168offline checks; live validation is pending in152. The source-import discovery change was in151, where it helped one removal but did not establish comprehensive discovery.

See [machine-readable identities](current-panel-summary.json) and [the requirement audit](completion-audit.md). The factory has demonstrated autonomous execution across diverse inputs; reliable scientific acceptance/rejection without operator qualification is still incomplete. R support remains deferred.
