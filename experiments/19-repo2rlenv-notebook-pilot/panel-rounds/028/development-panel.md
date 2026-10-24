# Current ten-domain Python development panel

This is a development panel across recorded factory versions, not a single-version holdout. The latest case per source is shown; native controls are separate from full task qualification and release.

| Domain | Original notebook | Latest campaign | Current evidence |
| --- | --- | --- | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | 133 | [native passed contract inconsistency hold](../../panel-rounds/026/result-133.json) |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | 134 | [generated review rejection with evidence visibility gap](../../panel-rounds/026/result-134.json) |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | 144 | [generated probe coverage rejection](../../panel-rounds/028/result-144.json) |
| Physiological signal analysis | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | 136 | [generated input adapter rejection](../../panel-rounds/026/result-136.json) |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | 137 | [generated comparison rejection with precision failure](../../panel-rounds/026/result-137.json) |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | 138 | [native passed source population review hold](../../panel-rounds/026/result-138.json) |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | 139 | [native validated private rights unestablished](../../panel-rounds/026/result-139.json) |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | 140 | [native validated dependency fixture review pending](../../panel-rounds/026/result-140.json) |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | 142 | [generated contract rejection after one repair](../../panel-rounds/026/result-142.json) |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | 143 | [unsupported conversion profile](../../panel-rounds/028/result-143.json) |

10 latest cases have terminal original-evidence audits, running: 0; frozen but unsubmitted: 0. 4 passed native controls; qualification holds remain. Five terminal cases reject generated setup/tasks; one stops at unsupported notebook conversion. These are not demonstrated broken source notebooks. Earlier Matchms135 infrastructure failure is preserved;144 is a fresh run. Earlier PyHMMER124 remains the latest qualified public release and is not substituted for134 here.

PyRadiomics141 remains on its execution/access hold and is not counted as a tested tenth notebook. PyMC143 is the selected tenth domain; original source and all branches remain intact, with suitability left to the factory. R support stays deferred.
