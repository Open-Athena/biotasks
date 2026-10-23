# Heart Rate Variability of a 5-Minute Resting ECG Recording

## Objective

You are given a single-subject ~5-minute physiological recording (`/inputs/bio_resting_5min_100hz.csv`: a CSV with columns `ECG`, `PPG`, `RSP`, uniformly sampled at 100 Hz; only the **ECG** channel is used). Compute the standard heart-rate-variability (HRV) index set of this recording in the **time domain**, the **frequency domain**, and the **nonlinear domain**, and also produce the **combined all-domain index table**. Produce the four output tables described under "Required outputs".

You may use any implementation; a compatible offline environment (NeuroKit2 0.2.13 pinned) can be supplied for convenience, but its use is not a requirement — outputs are graded against the methodology contract below.

## Methodology (defines the requested quantities)

All definitions follow the standard HRV literature as operationalized in NeuroKit2's HRV module (Pham et al. 2021, doi:10.3390/s21123998, is the reference review).

1. **R-peak detection on the raw ECG channel.** Detect R-peaks directly on the uncleaned, unfiltered ECG signal using the gradient-based QRS detector ("neurokit" method; no ECG cleaning, no artifact/ectopic-beat correction). This detector: computes the absolute derivative of the ECG, smooths it with a 0.1 s boxcar, marks QRS complexes where that envelope exceeds 1.5× its own 0.75 s boxcar-smoothed version, discards QRS complexes shorter than 40% of the mean QRS width, takes within each surviving QRS the local maximum of greatest prominence as the R-peak, and enforces a minimum 0.3 s delay between accepted peaks.

2. **RR interval series.** RR intervals (in milliseconds) as differences of consecutive R-peak sample indices divided by the sampling rate; non-finite intervals dropped. No detrending, interpolation, or artifact correction is applied to this series for the time and nonlinear domains.

3. **Time-domain indices** (RR in ms; sample standard deviations use ddof=1 throughout): MeanNN, SDNN; SDANN1/SDNNI1 for 1-minute averaging windows, and SDANN2/SDNNI2, SDANN5/SDNNI5 for 2- and 5-minute windows (any window length for which fewer than three complete windows fit the recording is left empty rather than 0); RMSSD, SDSD, CVNN, CVSD, MedianNN, MadNN, MCVNN, IQRNN, SDRMSSD, Prc20NN, Prc80NN, pNN50, pNN20, MinNN, MaxNN; HTI (triangular index) and TINN (triangular interpolation of the NN interval histogram), both from a histogram of the RR intervals with bin width 1000/128 ms. pNN50/pNN20 are percentages over the count of successive differences plus one.

4. **Frequency-domain indices.** Interpolate the RR series to an evenly spaced 100 Hz signal (quadratic, i.e., second-order spline, interpolation; constant values at the ends). Compute the power spectral density by Welch's method with Hann window, density scaling, no per-segment detrending beyond the constant mean subtraction, with the segment length chosen from the recording's frequency resolution (window sized to capture at least two cycles of the resolution frequency, capped at half the sample length) and zero padding to twice the segment length. Normalize the PSD by its maximum value. Band powers = trapezoidal integration of the normalized PSD over the discrete spectrum bins with the standard band edges: ULF (0–0.0033 Hz), VLF (0.0033–0.04 Hz), LF (0.04–0.15 Hz), HF (0.15–0.4 Hz), VHF (0.4–0.5 Hz); the spectrum is restricted to frequencies between the resolution floor and 0.5 Hz, and a band whose power integrates to exactly zero is reported empty rather than 0. Also report TP (sum of the five band powers, missing ones ignored), LFHF = LF/HF, LFn = LF/TP, HFn = HF/TP, LnHF = ln(HF).

5. **Nonlinear-domain indices**:
   - Poincaré: SD1, SD2, SD1SD2, ellipse area S = pi·SD1·SD2, CSI = 4·SD2/(4·SD1), CVI = log10(16·SD1·SD2), CSI_Modified = (4·SD2)²/(4·SD1).
   - Heart-rate fragmentation (Costa 2017): PIP, IALS, PSS, PAS on the successive-difference series.
   - Heart-rate asymmetry (Guzik, Porta, Piskorski): GI, SI, AI, PI (in percent), C1d, C1a, SD1d, SD1a, C2d, C2a, SD2d, SD2a, Cd, Ca, SDNNd, SDNNa.
   - DFA: DFA_alpha1 (short-term, window scales 4–11 beats), DFA_alpha2 (long-term, window scales from 12 beats up to (N+1)/10 beats); for each range also the multifractal spectrum summaries (q from −5 to 5): MFDFA_<alpha1|alpha2>_Width, _Peak, _Mean, _Max, _Delta, _Asymmetry, _Fluctuation, _Increment.
   - Complexity: ApEn, SampEn, FuzzyEn (embedding dimension 2, delay 1, tolerance 0.2 × SD of the RR series); ShanEn (Shannon entropy of the value distribution, base 2); multiscale sample entropy MSEn (non-overlapping coarse-graining), CMSEn (time-shift composite) and RCMSEn (refined composite), each with dimension 2, the same tolerance, scale factors 1..N/(dimension+10), point estimate = sum over scales; CD (correlation dimension, dimension 2), HFD (Higuchi, kmax 10), KFD (Katz), LZC (Lempel-Ziv complexity).
   - Symbolic dynamics: quantize the RR series into 4 equal-probability levels, form consecutive 3-symbol words, and report the proportions of words in the four variation families 0V, 1V, 2LV, 2UV.

## Required outputs

Write to your output directory (create it if needed) four CSV files, each with a header row and **exactly one data row**, index values in the natural units above (RR in ms; frequency powers on the normalized-PSD scale, i.e., unitless relative powers; ratios and entropies unitless). Column names carry the prefix `HRV_`. Empty fields denote "not defined for this recording". Columns are identified by name; their order in the file is free.

- `hrv_time.csv` — `HRV_MeanNN, HRV_SDNN, HRV_SDANN1, HRV_SDNNI1, HRV_SDANN2, HRV_SDNNI2, HRV_SDANN5, HRV_SDNNI5, HRV_RMSSD, HRV_SDSD, HRV_CVNN, HRV_CVSD, HRV_MedianNN, HRV_MadNN, HRV_MCVNN, HRV_IQRNN, HRV_SDRMSSD, HRV_Prc20NN, HRV_Prc80NN, HRV_pNN50, HRV_pNN20, HRV_MinNN, HRV_MaxNN, HRV_HTI, HRV_TINN`
- `hrv_frequency.csv` — `HRV_ULF, HRV_VLF, HRV_LF, HRV_HF, HRV_VHF, HRV_TP, HRV_LFHF, HRV_LFn, HRV_HFn, HRV_LnHF`
- `hrv_nonlinear.csv` — `HRV_SD1, HRV_SD2, HRV_SD1SD2, HRV_S, HRV_CSI, HRV_CVI, HRV_CSI_Modified, HRV_PIP, HRV_IALS, HRV_PSS, HRV_PAS, HRV_GI, HRV_SI, HRV_AI, HRV_PI, HRV_C1d, HRV_C1a, HRV_SD1d, HRV_SD1a, HRV_C2d, HRV_C2a, HRV_SD2d, HRV_SD2a, HRV_Cd, HRV_Ca, HRV_SDNNd, HRV_SDNNa, HRV_DFA_alpha1, HRV_MFDFA_alpha1_Width, HRV_MFDFA_alpha1_Peak, HRV_MFDFA_alpha1_Mean, HRV_MFDFA_alpha1_Max, HRV_MFDFA_alpha1_Delta, HRV_MFDFA_alpha1_Asymmetry, HRV_MFDFA_alpha1_Fluctuation, HRV_MFDFA_alpha1_Increment, HRV_DFA_alpha2, HRV_MFDFA_alpha2_Width, HRV_MFDFA_alpha2_Peak, HRV_MFDFA_alpha2_Mean, HRV_MFDFA_alpha2_Max, HRV_MFDFA_alpha2_Delta, HRV_MFDFA_alpha2_Asymmetry, HRV_MFDFA_alpha2_Fluctuation, HRV_MFDFA_alpha2_Increment, HRV_ApEn, HRV_SampEn, HRV_ShanEn, HRV_FuzzyEn, HRV_MSEn, HRV_CMSEn, HRV_RCMSEn, HRV_CD, HRV_HFD, HRV_KFD, HRV_LZC, HRV_Symbolic_EqualProb4_0V, HRV_Symbolic_EqualProb4_1V, HRV_Symbolic_EqualProb4_2LV, HRV_Symbolic_EqualProb4_2UV`
- `hrv_indices.csv` — the combined all-domain table: the column set of `hrv_time.csv` followed by that of `hrv_frequency.csv` followed by that of `hrv_nonlinear.csv`. Matching column names across the combined table and the per-domain tables must carry identical values (the combined extraction runs the same three domain computations).

## Environment and resource limits

Solving is offline (no network access for data or packages beyond what is pre-staged). The input is supplied at `/inputs/bio_resting_5min_100hz.csv`. Budget: 4 CPUs, 8 GiB memory, 10 GiB disk, 600 s wall-clock. Any analysis software may be used provided it meets the output contract above.
