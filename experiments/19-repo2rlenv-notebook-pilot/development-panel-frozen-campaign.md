# Frozen ten-notebook comparison

All ten original notebook inputs now have actual immutable payloads. Every payload was read and compared: its selected source SHA-256 matches the original panel, all 165 executable factory files match runtime `417df0ed95e0c55ef12a91d264f5e1c220e8b3be` byte-for-byte, and the resource/time/network/model policy is unchanged. See [the complete freeze record](development-panel-frozen-campaign.json). Different input checkpoint revisions add source/configuration metadata; they do not change this executable factory.

| Domain | Original notebook | Campaign | State at freeze |
| --- | --- | --- | --- |
| Transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | `autonomous-scanpy-clustering-031` | prepared not submitted |
| Regulatory genomics | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | `autonomous-motifs-032` | prepared not submitted |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | `autonomous-rmsd-033` | prepared not submitted |
| Medical imaging | [pyradiomics-brain](https://github.com/AIM-Harvard/pyradiomics/blob/8ed579383b44806651c463d5e691f3b2b57522ab/notebooks/RadiomicsExample.ipynb) | `autonomous-pyradiomics-brain-030` | prepared not submitted |
| Proteomics | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | `autonomous-psm-026` | prepared not submitted |
| Metabolomics | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | `autonomous-spectra-027` | prepared not submitted |
| Physiology | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | `autonomous-hrv-024` | submitted outcome pending |
| Metabolic systems biology | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | `autonomous-deletions-028` | prepared not submitted |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | `autonomous-relatedness-029` | prepared not submitted |
| Protein sequence analysis | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | `autonomous-pyhmmer-025` | submitted outcome pending |

This freeze records input and runtime identities. Only 024 and 025 have been submitted at this checkpoint; no new model or scientific execution was done to build these payloads. All eight remaining cases await a free slot and an aggregate-budget reservation. R support remains deferred.

Historical Bioframe 014 and MDAnalysis 017 used earlier factory versions. Their positive and negative results remain intact, while fresh original-source 032 and 033 complete this same-factory panel. The older operator-assisted Scanpy release also does not substitute for fresh autonomous 031.

Do not change a seed or generated task to obtain a passing result. Workers choose endpoints, tasks, graders and scientific repairs through the existing versioned prompts. Record validated tasks, explicit generated-candidate/source rejections and infrastructure failures separately. This selected development panel is not held-out or representative evidence.

The four previously private notebook inputs remain in the local-only input checkpoint and approved private run archives; this metadata record does not publish those raw files or grant blanket data-redistribution permission. Publication of any new task still depends on its actual input terms and validation evidence.
