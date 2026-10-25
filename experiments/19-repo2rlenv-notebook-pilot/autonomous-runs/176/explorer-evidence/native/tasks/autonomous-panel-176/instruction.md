# Heart rate variability (HRV) indices for a 5-minute resting ECG recording

## Objective

You are given a 5-minute multi-channel physiological recording of a participant at rest (ECG, PPG, RSP), sampled at 100 Hz. Using the **ECG channel**, determine R-peak occurrences, derive the R–R (NN) interval series, and compute the participant's heart-rate-variability indices in the time domain, the frequency domain, the non-linear domain, and as a combined all-domain summary.

The reference pipeline is the standard, default HRV computation of **NeuroKit2 version 0.2.13** (`nk.hrv_time`, `nk.hrv_frequency` with `normalize=True`, `nk.hrv_nonlinear`, `nk.hrv` with `sampling_rate=100`). A reference execution environment (Python 3.13 with `neurokit2==0.2.13`, `numpy==2.5.4`, `scipy==1.18.1`, `pandas==2.3.3`) is available in the sandbox for convenience, but you may use any implementation that produces the requested quantities. Output values must be reported for the same indices, with the same definitions, as this preset.

## Input

`inputs/bio_resting_5min_100hz.csv` — a comma-separated file with a header row and three numeric columns `ECG`, `PPG`, `RSP`, giving samples of a resting recording at **100 Hz** (consecutive rows are consecutive samples, 10 ms apart; 30,000 rows). Use the `ECG` column only.

## Method

1. **R-peak detection.** Detect R-peak sample indices in the raw ECG column with the default NeuroKit2 R-peak finder (`method="neurokit"`), at `sampling_rate=100`. Do **not** apply artifact correction to the detected peaks (`correct_artifacts=False`) and do not substitute a different detector or a pre-cleaned series; the detected peak set defines the beat population for all subsequent indices.
2. **R–R intervals.** From the detected peak indices, form the successive-difference NN interval series in **milliseconds**, based on the 100 Hz sampling.
3. **Time-domain indices.** Compute the standard time-domain HRV statistics of the NN series (ms units): mean (MeanNN), standard deviation (SDNN), RMSSD/SDSD, coefficient-of-variation indices, median/MAD/IQR, 20th/80th percentiles, pNN50/pNN20 (percent of successive differences exceeding 50 ms / 20 ms), minimum/maximum NN, Henrich triangle index and TINN, and the SDANN/SDNNI statistics over **1-minute** windows. Indices that require longer recordings than 5 minutes (SDANN2, SDNNI2, SDANN5, SDNNI5) are undefined for this input and must be reported as empty.
4. **Frequency-domain indices.** Interpolate the NN series onto a uniform 100 Hz grid, estimate the power spectral density with **Welch's method** (Hann window, mean averaging, spectral density scaling, no per-segment detrending), **normalize the PSD by its maximum value**, and integrate band power over: ULF 0–0.0033 Hz (undefined for a 5-minute recording → empty), VLF 0.0033–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.4 Hz, VHF 0.4–0.5 Hz. Report the band powers, the total power (sum over the bands), the LF/HF ratio, the LF and HF fractions of total power (`LFn`, `HFn`), and the natural logarithm of HF power (`LnHF`).
5. **Non-linear indices.** Compute the standard default non-linear indices of the NN series: Poincaré SD1, SD2, their ratio and ellipse area; CSI, CVI and modified CSI; PIP, IALS, PSS, PAS; Guzik and Porta indices (GI, SI, AI, PI); asymmetric Poincaré decomposition (C1d/C1a, SD1d/SD1a, C2d/C2a, SD2d/SD2a, Cd/Ca, SDNNd/SDNNa); DFA short- and long-term scaling exponents (alpha1, alpha2) and the multifractal-DFA alpha1/alpha2 summary statistics (Width, Peak, Mean, Max, Delta, Asymmetry, Fluctuation, Increment); approximate, sample, Shannon, fuzzy and multiscale entropies (ApEn, SampEn, ShanEn, FuzzyEn, MSEn, CMSEn, RCMSEn); correlation dimension (CD), Higuchi and Katz fractal dimensions (HFD, KFD), Lempel-Ziv complexity (LZC), and the equal-probability 4-symbol symbolic-dynamics proportions (0V, 1V, 2LV, 2UV patterns).
6. **Combined table.** Produce the same three domain outputs obtained from the domain functions used at their **default settings** (including PSD normalization at the default) and concatenate them column-wise into one table. No respiration-derived indices are included (no RSP columns are passed).

For any index whose NeuroKit2-0.2.13 default settings matter (entropy tolerance `r`, DFA window ranges, MST/max-scale for multiscale entropy, symbolic pattern length), the reference preset's defaults — not the original literature conventions — define the requested quantity.

## Outputs

Write four comma-separated files (header row of index names, one value row, no index column), with empty fields for undefined indices:

- `outputs/hrv_time.csv` — the time-domain indices.
- `outputs/hrv_freq.csv` — the frequency-domain indices (with PSD normalized by maximum, as above).
- `outputs/hrv_nonlinear.csv` — the non-linear indices.
- `outputs/hrv_indices.csv` — the combined table of the three domains at default settings.

Index names follow the `HRV_` prefix convention of the reference preset (e.g., `HRV_MeanNN`, `HRV_RMSSD`, `HRV_LF`, `HRV_SD1`, `HRV_SampEn`). Each output must report a value (or an empty field, where undefined) for every index that the reference preset's default computation returns for this input.

## Resources

Offline execution, 4 CPUs, 8 GiB RAM, ≤ 10 GiB disk; your program must finish within 600 seconds. Reference execution of this analysis completes in well under one minute on the provided environment.

## Acceptance rules

# Acceptance rules (addendum)

## Files and paths
Four output files are required, each read at its declared path relative to the supplied output root (no extra directory layer, no fallback search):

- `hrv_time.csv` — time-domain indices
- `hrv_freq.csv` — frequency-domain indices (PSD normalized by maximum)
- `hrv_nonlinear.csv` — non-linear indices
- `hrv_indices.csv` — combined all-domain table

Any missing file, unreadable file, or file placed at any other path (including under an extra `outputs/` subdirectory) fails the corresponding checks.

## File format
Each file is a comma-separated UTF-8 text file: one header row of `HRV_` index names followed by exactly one data row, with no index column. Any other shape (no data row, more than one data row, ragged row, extra blank line after the single record ends, duplicated or empty header names) fails the structural check. Quoted fields are decoded with standard CSV rules. Every data field must be either an empty field or a decimal numeric literal that parses to a finite value; `NaN`, `inf`, nonfinite tokens, and any non-numeric content fail. Column order within the header is not graded; column identity is by exact case-sensitive `HRV_` index name.

## Column sets
For each file, the set of column names must equal the reference set for that file exactly: every reference index present (no missing values masked by omission), no extra columns, and no renamed indices. The reference sets are the NeuroKit2-0.2.13 default index sets for this input: 25 columns in `hrv_time.csv` (`HRV_MeanNN` through `HRV_TINN`), 10 in `hrv_freq.csv` (`HRV_ULF` through `HRV_LnHF`), 60 in `hrv_nonlinear.csv`, and 95 in `hrv_indices.csv` (the column union of the three domain files; no respiration-derived indices).

## Undefined indices (empty fields)
Indices that the reference computation returns as undefined for a 5-minute recording — `HRV_ULF`, `HRV_SDANN2`, `HRV_SDNNI2`, `HRV_SDANN5`, `HRV_SDNNI5` — must be written as empty fields. Zero, `NaN`, or any numeric substitute in place of an undefined index fails, as does reporting a value in the reference-position empty field. Conversely, every index with a reference value must carry a numeric field; an empty field there fails.

## Numeric comparison
Values are compared after parsing, on the decoded scientific value, per column matched by index name.

A submission value `s` matches the reference value `r` when

  |s − r| ≤ 1e-9 + 1e-9 · |r|   (reference value as denominator; both sides in the same reported units)

This bound is a limit on observable output differences. It accepts small serialization/hand-off round-off of the written decimal representation (an ordinary CSV write/read round trip of the reported values must not change grading), but any deviation beyond it — including one milli in a millisecond-unit index, a percent-level change produced by different preprocessing settings (e.g. artifact-corrected or substituted R peaks, unnormalized PSD, different entropy tolerance or DFA window settings), or values from a different beat population — fails. The comparison is symmetric in absolute terms but anchored to the reference magnitude; scientific quantities are compared in the units stated for each index (milliseconds for NN-based time-domain indices, dimensionless normalized powers/ratios for frequency and non-linear domains).

Empty-field positions must match exactly; a submission with a value where the reference is undefined, or an empty field where the reference has a value, fails regardless of the numeric comparison.

## Cross-file consistency
`hrv_indices.csv` is graded against the submission's own three domain files: its column set must equal the union of the submission's `hrv_time.csv`, `hrv_freq.csv` and `hrv_nonlinear.csv` column sets, and each shared index must carry the same value, under the same numeric rule, as in the corresponding domain file (empty-field status included). The three domain files must also be mutually consistent on any index name they share. A correct-looking combined table cannot compensate for value errors in the domain files; each file is graded separately, and every check must pass.

## Verdict
All checks (structure, the four per-file value checks, and cross-file consistency) must pass. The grader reports pass/fail per check and always exits 0 after writing its report; a crash or malformed submission is a failed check, not a successful run.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
