# Heart-rate variability indices for a 5-minute resting ECG recording

## Objective

From the supplied 5-minute resting physiological recording, compute the complete set of heart-rate-variability (HRV) indices — time-domain, frequency-domain and non-linear-domain — that the analysis pipeline defined by **NeuroKit2 0.2.13** (the versioned reference preset for this task) produces from R-peaks detected in the ECG channel. The requested results are the 95 HRV index values listed under "Required output" below.

## Supplied input

- `input/bio_resting_5min_100hz.csv` — a text CSV with a header row `ECG,PPG,RSP` and one row per sample of a 5-minute recording acquired at 100 Hz (three columns: ECG, PPG, respiration). Only the **ECG** column is used by this analysis; PPG and RSP are present but unused.

## Method (conventional steps identified by the reference preset)

1. **R-peak detection** — on the ECG column *exactly as supplied* (no separate ECG-cleaning step is part of this analysis, and no artifact correction is applied), using NeuroKit2 0.2.13's default peak-detection method (`ecg_peaks` with `method="neurokit"`, `correct_artifacts=False`), sampling rate 100 Hz.
2. **HRV computation from the resulting R-peak series**, sampling rate 100 Hz, in all three domains exactly as defined by NeuroKit2 0.2.13's `hrv_time`, `hrv_frequency` and `hrv_nonlinear`:
   - **Time domain:** standard NN-interval statistics (mean, SD, RMSSD, pNNx, histogram indices, etc.), with NN intervals in **milliseconds**.
   - **Frequency domain:** RR series interpolated at 100 Hz; power spectral density estimated by the Welch method and **normalized by its maximum value** before band integration (as in the source's `normalize=True`); band edges: ultra-low 0–0.0033 Hz, very-low 0.0033–0.04 Hz, low 0.04–0.15 Hz, high 0.15–0.4 Hz, very-high 0.4–0.5 Hz; plus total power (TP), LF/HF ratio, normalized LF (LFn = LF/TP), normalized HF (HFn = HF/TP) and LnHF. Band powers are unitless (relative power on the normalized PSD).
   - **Non-linear domain:** Poincaré indices (SD1/SD2 and asymmetric variants), CSI/CVI, DFA and multifractal-DFA exponents, sample/approximate/fuzzy/multiscale entropies, Shannon entropy, and the remaining indices produced by `hrv_nonlinear` (symbolic dynamics with equal-probability 4-level coding, etc.).

Using NeuroKit2 0.2.13 directly is permitted (a compatible environment is available), but any tool is acceptable provided the requested quantities are the ones defined by this preset. Do not change the peak-detection method, artifact-correction setting, band edges, PSD method, normalization rule or sampling rate — these define the quantities being requested.

## Required output

A single file `outputs/hrv_indices.csv`: header row with the metric names below, one data row with the value for each metric. Column order is free — values are identified by column name. Metrics that are undefined for this recording (undefined per the reference method) must be left as empty fields. All 95 columns must be present:

Time domain: `HRV_MeanNN`, `HRV_SDNN`, `HRV_SDANN1`, `HRV_SDNNI1`, `HRV_SDANN2`, `HRV_SDNNI2`, `HRV_SDANN5`, `HRV_SDNNI5`, `HRV_RMSSD`, `HRV_SDSD`, `HRV_CVNN`, `HRV_CVSD`, `HRV_MedianNN`, `HRV_MadNN`, `HRV_MCVNN`, `HRV_IQRNN`, `HRV_SDRMSSD`, `HRV_Prc20NN`, `HRV_Prc80NN`, `HRV_pNN50`, `HRV_pNN20`, `HRV_MinNN`, `HRV_MaxNN`, `HRV_HTI`, `HRV_TINN`.

Frequency domain: `HRV_ULF`, `HRV_VLF`, `HRV_LF`, `HRV_HF`, `HRV_VHF`, `HRV_TP`, `HRV_LFHF`, `HRV_LFn`, `HRV_HFn`, `HRV_LnHF`.

Non-linear domain: `HRV_SD1`, `HRV_SD2`, `HRV_SD1SD2`, `HRV_S`, `HRV_CSI`, `HRV_CVI`, `HRV_CSI_Modified`, `HRV_PIP`, `HRV_IALS`, `HRV_PSS`, `HRV_PAS`, `HRV_GI`, `HRV_SI`, `HRV_AI`, `HRV_PI`, `HRV_C1d`, `HRV_C1a`, `HRV_SD1d`, `HRV_SD1a`, `HRV_C2d`, `HRV_C2a`, `HRV_SD2d`, `HRV_SD2a`, `HRV_Cd`, `HRV_Ca`, `HRV_SDNNd`, `HRV_SDNNa`, `HRV_DFA_alpha1`, `HRV_MFDFA_alpha1_Width`, `HRV_MFDFA_alpha1_Peak`, `HRV_MFDFA_alpha1_Mean`, `HRV_MFDFA_alpha1_Max`, `HRV_MFDFA_alpha1_Delta`, `HRV_MFDFA_alpha1_Asymmetry`, `HRV_MFDFA_alpha1_Fluctuation`, `HRV_MFDFA_alpha1_Increment`, `HRV_DFA_alpha2`, `HRV_MFDFA_alpha2_Width`, `HRV_MFDFA_alpha2_Peak`, `HRV_MFDFA_alpha2_Mean`, `HRV_MFDFA_alpha2_Max`, `HRV_MFDFA_alpha2_Delta`, `HRV_MFDFA_alpha2_Asymmetry`, `HRV_MFDFA_alpha2_Fluctuation`, `HRV_MFDFA_alpha2_Increment`, `HRV_ApEn`, `HRV_SampEn`, `HRV_ShanEn`, `HRV_FuzzyEn`, `HRV_MSEn`, `HRV_CMSEn`, `HRV_RCMSEn`, `HRV_CD`, `HRV_HFD`, `HRV_KFD`, `HRV_LZC`, `HRV_Symbolic_EqualProb4_0V`, `HRV_Symbolic_EqualProb4_1V`, `HRV_Symbolic_EqualProb4_2LV`, `HRV_Symbolic_EqualProb4_2UV`.

(These columns exactly cover the notebook's per-domain and combined results: the notebook's three domain tables are column subsets of this one table for the same peak series and the same parameters.)

## Constraints

- Execution is offline; no network access. CPU only (4 cores), 8 GiB RAM, 10 GiB disk; 600 s runtime limit.
- Figures generated along the way are not part of the deliverable.
