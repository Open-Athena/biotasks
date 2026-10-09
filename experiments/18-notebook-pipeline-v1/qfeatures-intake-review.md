# QFeatures input preparation

The seed calls MsDataHub::cptac_a_b_peptides.txt(). MsDataHub's official metadata identifies the source as msdata, SourceVersion 1.0, rather than the separate CPTAC A/B/C teaching-table URL. The exact A/B table is staged from bioc/msdata revision f4aba520b209e21ddd9816b0054fa74948cc9ef8, inst/quant/cptac_a_b_peptides.txt; source URL, size and checksum are in qfeatures-inputs.json. The source DESCRIPTION declares msdata 0.53.1 and GPL (>=2). Preserve attribution and data-package terms.

Streaming inspection found 11466 rows and 71 columns. The six raw quantitative column names are Intensity 6A_7, Intensity 6A_8, Intensity 6A_9, Intensity 6B_7, Intensity 6B_8 and Intensity 6B_9. R read.delim converts spaces in column names to dots; a language-neutral instruction should identify the actual input columns and explicitly permit that representation change. The measurements are processed quantitative proteomics values, not a newly simulated table.

The seed removes Reverse and Potential.contaminant rows, converts zero intensities to missing, and removes peptides with any missing sample value. Its later aggregation groups by the Proteins annotation (protein groups, potentially semicolon-delimited), after log transformation and normalization, using robustSummary by default. The compact task must explicitly state which of those transformations it retains and which aggregation it uses; do not silently split protein-group identifiers or swap raw and normalized intensities. Native QFeatures reference execution remains required. No analysis has run.

Primary dataset description: https://rformassspectrometry.github.io/MsDataHub/articles/MsDataHub.html .
