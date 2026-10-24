# Current ten-source development assessment

Latest independently archived completed outcome per source. This combines development versions; it is not a held-out success-rate estimate. Original failed attempts remain preserved. Active 147/149 repeats are excluded from the completed-outcome counts.

| Domain | Source | Campaign | Pipeline minutes | Accounted model requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | cobrapy-deletions | [133](../../panel-rounds/026/result-133.json) | 37.30 | 110 | Native controls complete; qualification held |
| Protein sequence profiles | pyhmmer-msa-to-hmm | [134](../../panel-rounds/026/result-134.json) | 54.17 | 154 | Generated candidate rejected |
| Metabolite mass spectra | matchms-spectral-matching | [144](../../panel-rounds/028/result-144.json) | 79.58 | 152 | Generated candidate rejected |
| Physiological signals | neurokit-hrv | [136](../../panel-rounds/026/result-136.json) | 4.48 | 25 | Generated candidate rejected |
| Single-cell transcriptomics | https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb | [137](../../panel-rounds/026/result-137.json) | 89.46 | 134 | Generated candidate rejected |
| Genomic intervals | bioframe-motifs-to-peaks | [138](../../panel-rounds/026/result-138.json) | 39.14 | 102 | Native controls complete; qualification held |
| Proteomic search results | pyteomics-filtering | [139](../../panel-rounds/026/result-139.json) | 40.82 | 122 | Native controls complete; qualification held |
| Molecular dynamics | mdanalysis-rmsd | [148](../../panel-rounds/031/result-148.json) | 50.03 | 107 | Incomplete native infrastructure; cleanup reconciled |
| Statistical genetics | sgkit-relatedness | [142](../../panel-rounds/026/result-142.json) | 109.15 | 180 | Generated candidate rejected |
| Bayesian biological inference | pymc-rat-tumor | [145](../../panel-rounds/029/result-145.json) | 77.02 | 139 | Qualified, published and download verified |

Four completed native-control sets are distinct from scientific qualification: only the latest PyMC task is qualified/published in this table. Earlier qualified public tasks, including PyHMMER124, are retained separately rather than substituted for the latest outcomes. Five generated-candidate rejections expose remaining factory weaknesses. MDAnalysis148 additionally passed 18 scientific controls and its native reference, but provider deletion outlasted its bounded cleanup check; the empty control and solver did not run. Its complete original evidence and later five-owner absence are verified.

Across these ten outcomes, measured pipeline time ranges from 4.48 to 109.15 minutes. The four cases completing native controls range from 37.30 to 77.02 minutes. These exclude bootstrap, archive verification and publication. Short failed setup attempts do not estimate successful generation throughput.

The next evidence is147for general independently additive negative coverage, and149for an unchanged source-only autonomous retry after148provider cleanup failure. Do not claim those features reliable from plans or synthetic checks. No case-specific scientific edits or diagnostic hints are supplied to those fresh workers.

See [the complete machine-readable identities](current-panel-summary.json) for original archive and public receipt hashes. Computational reproduction does not establish biological validity; the development panel does not establish unseen-notebook generality.
