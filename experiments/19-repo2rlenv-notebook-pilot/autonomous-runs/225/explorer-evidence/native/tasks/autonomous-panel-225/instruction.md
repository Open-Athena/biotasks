# Heart-rate variability indices for a 5-minute resting ECG recording

## Objective

From the supplied 5-minute resting physiological recording, compute the complete set of heart-rate-variability (HRV) indices — time-domain, frequency-domain and non-linear-domain — produced by the analysis preset defined by **NeuroKit2 0.2.13** from R-peaks detected in the ECG channel. The requested result is the 95 HRV index values listed under "Required output".

## Supplied input

- `inputs/bio_resting_5min_100hz.csv` — text CSV with header row `ECG,PPG,RSP` and one row per sample of a 5-minute recording acquired at 100 Hz (columns: ECG, PPG, respiration). Only the **ECG** column is used by this analysis; PPG and RSP are present but unused.

## Method (the preset that defines the requested quantities)

1. **R-peak detection** on the ECG column exactly as supplied (no ECG-cleaning step and no artifact correction are part of this analysis), using NeuroKit2 0.2.13's default peak-detection method (`ecg_peaks` with `method="neurokit"`, `correct_artifacts=False`), sampling rate 100 Hz.
2. **HRV computation from the resulting R-peak series**, sampling rate 100 Hz, in all three domains exactly as defined by NeuroKit2 0.2.13's `hrv_time`, `hrv_frequency` and `hrv_nonlinear`:
   - **Time domain:** standard NN-interval statistics (mean, SD, RMSSD, pNNx, histogram indices, etc.), with NN intervals in **milliseconds**.
   - **Frequency domain:** RR series interpolated at 100 Hz; power spectral density estimated by the Welch method and normalized by its maximum value before band integration (as with `normalize=True`); band edges: ultra-low 0–0.0033 Hz, very-low 0.0033–0.04 Hz, low 0.04–0.15 Hz, high 0.15–0.4 Hz, very-high 0.4–0.5 Hz; plus total power (TP), LF/HF ratio, normalized LF (LFn = LF/TP), normalized HF (HFn = HF/TP) and LnHF. Band powers are unitless (relative power on the normalized PSD).
   - **Non-linear domain:** Poincaré indices (SD1/SD2 and asymmetric variants), CSI/CVI, DFA and multifractal-DFA exponents, approximate/sample/fuzzy/multiscale entropies, Shannon entropy, correlation/Higuchi/Katz dimensions, Lempel-Ziv complexity, and the remaining indices produced by `hrv_nonlinear` (symbolic dynamics with equal-probability 4-level coding, etc.).

Using NeuroKit2 0.2.13 directly is permitted (it is installed in the execution environment), but any tool is acceptable provided the requested quantities are the ones defined by this preset. Do not change the peak-detection method, artifact-correction setting, band edges, PSD method, normalization rule or sampling rate — these define the quantities being requested.

## Required output

A single file `outputs/hrv_indices.csv`: a header row with the metric names below and one data row with the value of each metric. Column order is free — values are identified by column name. Metrics that are undefined for this recording (undefined per the reference method) must be left as empty fields. All 95 columns must be present:

Time domain: `HRV_MeanNN`, `HRV_SDNN`, `HRV_SDANN1`, `HRV_SDNNI1`, `HRV_SDANN2`, `HRV_SDNNI2`, `HRV_SDANN5`, `HRV_SDNNI5`, `HRV_RMSSD`, `HRV_SDSD`, `HRV_CVNN`, `HRV_CVSD`, `HRV_MedianNN`, `HRV_MadNN`, `HRV_MCVNN`, `HRV_IQRNN`, `HRV_SDRMSSD`, `HRV_Prc20NN`, `HRV_Prc80NN`, `HRV_pNN50`, `HRV_pNN20`, `HRV_MinNN`, `HRV_MaxNN`, `HRV_HTI`, `HRV_TINN`.

Frequency domain: `HRV_ULF`, `HRV_VLF`, `HRV_LF`, `HRV_HF`, `HRV_VHF`, `HRV_TP`, `HRV_LFHF`, `HRV_LFn`, `HRV_HFn`, `HRV_LnHF`.

Non-linear domain: `HRV_SD1`, `HRV_SD2`, `HRV_SD1SD2`, `HRV_S`, `HRV_CSI`, `HRV_CVI`, `HRV_CSI_Modified`, `HRV_PIP`, `HRV_IALS`, `HRV_PSS`, `HRV_PAS`, `HRV_GI`, `HRV_SI`, `HRV_AI`, `HRV_PI`, `HRV_C1d`, `HRV_C1a`, `HRV_SD1d`, `HRV_SD1a`, `HRV_C2d`, `HRV_C2a`, `HRV_SD2d`, `HRV_SD2a`, `HRV_Cd`, `HRV_Ca`, `HRV_SDNNd`, `HRV_SDNNa`, `HRV_DFA_alpha1`, `HRV_MFDFA_alpha1_Width`, `HRV_MFDFA_alpha1_Peak`, `HRV_MFDFA_alpha1_Mean`, `HRV_MFDFA_alpha1_Max`, `HRV_MFDFA_alpha1_Delta`, `HRV_MFDFA_alpha1_Asymmetry`, `HRV_MFDFA_alpha1_Fluctuation`, `HRV_MFDFA_alpha1_Increment`, `HRV_DFA_alpha2`, `HRV_MFDFA_alpha2_Width`, `HRV_MFDFA_alpha2_Peak`, `HRV_MFDFA_alpha2_Mean`, `HRV_MFDFA_alpha2_Max`, `HRV_MFDFA_alpha2_Delta`, `HRV_MFDFA_alpha2_Asymmetry`, `HRV_MFDFA_alpha2_Fluctuation`, `HRV_MFDFA_alpha2_Increment`, `HRV_ApEn`, `HRV_SampEn`, `HRV_ShanEn`, `HRV_FuzzyEn`, `HRV_MSEn`, `HRV_CMSEn`, `HRV_RCMSEn`, `HRV_CD`, `HRV_HFD`, `HRV_KFD`, `HRV_LZC`, `HRV_Symbolic_EqualProb4_0V`, `HRV_Symbolic_EqualProb4_1V`, `HRV_Symbolic_EqualProb4_2LV`, `HRV_Symbolic_EqualProb4_2UV`.

## Constraints

- Execution is offline; no network access. CPU only (4 cores), 8 GiB RAM, 10 GiB disk; 600 s runtime limit.
- Figures are not part of the deliverable; plotting may be disabled.

## Acceptance rules

## Acceptance rules for `hrv_indices.csv`

- **File and path**: a single file named `hrv_indices.csv` must exist directly at the declared output root (no extra directory layers such as `outputs/outputs/`).
- **Table shape**: the file is a comma-delimited CSV with decimal point, read with a strict RFC 4180-style reader; ordinary quoted fields are data. It must contain a header row and exactly one data row — no additional, blank or ragged records.
- **Columns**: the header must contain exactly the 95 named metric columns listed in "Required output", each appearing exactly once (no duplicates, no renames, no extras, none missing). Column order is free; values are identified by column name. The header names are compared literally after CSV unquoting, without whitespace stripping.
- **Values**: each field must be a plain decimal numeric literal (finite; scientific notation is acceptable). `NaN`, `Inf`, `-Inf` (literal or quoted) and any non-numeric text are rejected. A value for a metric that is undefined in the reference must be an explicit empty field (no characters between the delimiters), not a `NaN` marker; and where the reference is defined, an empty field is rejected.
- **Empty-field identity**: emptiness is part of the answer — a submission value where the reference has no defined value fails, and an empty field where the reference is defined fails.
- **Numeric comparison**: values are compared after parsing as 64-bit floating point; text formatting is otherwise free (digit count/floating repr not compared, provided the parsed value is finite and within tolerance). Each submission value must satisfy |submission − reference| ≤ 1e-6 · |reference| + 1e-9, with the denominator being the reference value's magnitude. Exact zero (as a reference value) is accepted only when the submission value is within the absolute floor of 1e-9. Nonfinite submissions never compare equal to anything.
- **Reference values**: tolerances are evaluated against the privately stored reference computation (NeuroKit2 0.2.13 preset defined in the method section); the grader does not reimplement the analysis in this step.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
