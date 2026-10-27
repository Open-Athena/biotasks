## Input derivation

- `input/bio_resting_5min_100hz.csv` = byte-identical staged copy (sha256 6a33ff8ae229f608354563044ff4a4d1c4e927c817e9269a4dec6173abefc385, 1,784,368 bytes) of the NeuroKit dataset file at source revision ff419d98, served via nk.data(). Header `ECG,PPG,RSP`; worker smoke test observed a 30000x3 DataFrame. Only the ECG column is consumed by the scientific pipeline; solver must detect peaks itself (no R-peak intermediate is supplied — peak detection is retained downstream work).
- The reference run used an environment-only adapter redirecting nk.data()'s remote URL prefix to the staged bytes; no method change (trial/source.diff).

## Endpoint lineage

- Graded target: single-row combined HRV table (all three domains), derived as: ECG column -> `nk.ecg_peaks(data["ECG"], sampling_rate=100)` (raw uncleaned ECG; neurokit2 0.2.13 defaults: method="neurokit", correct_artifacts=False, verified at ecg/ecg_peaks.py line 9) -> `nk.hrv_time/hrv_frequency/hrv_nonlinear` parameters (verified `hrv/hrv.py` lines 100–115): `hrv_time(peaks, sampling_rate=100)`, `hrv_frequency(peaks, sampling_rate=100)` using package defaults (Welch PSD, band edges ULF (0,0.0033), VLF (0.0033,0.04), LF (0.04,0.15), HF (0.15,0.4), VHF (0.4,0.5), interpolation_rate=100, normalize=True — the notebook's explicit `normalize=True` equals this default), `hrv_nonlinear(peaks, sampling_rate=100)`.
- Recorded reference artifacts: hrv_time.csv (4da5b39c…), hrv_freq.csv (81749e0b…), hrv_nonlinear.csv (8afda790…), hrv_indices.csv (e2dc559a…). The combined table's per-column value fingerprints are identical to the corresponding domain-table columns (output-audit.json), establishing the stated projection; the public task requires only the combined column set (95 columns) and documents this subsumption.
- `hrv_rsa` branch not executed and not part of the required schema (peaks input lacks RSP_Phase/RSP_Phase_Completion columns; hrv.py lines 109–113).

## Identity / semantics

- One data row; values identified by column name; column order carries no scientific meaning (identity by metric name). Multiplicity: exactly one value per metric name.
- Time-domain NN-based metrics: milliseconds. Frequency-domain band powers: unitless relative power (PSD normalized to peak = 1 before band integration), so not ms^2/Hz absolute powers — do not compare against unnormalized PSD band powers. LFn=LF/TP and HFn=HF/TP do not sum to 1 (TP includes VLF+VHF). Ratios and dimensionless indices unitless. Entropy log base not independently verified beyond package implementation — flag for validation if it becomes comparison-consequential.
- Missing values: metrics undefined for a 5-min recording serialize as empty fields in the reference CSVs (e.g. several SDANN/SDNNI variants and HRV_ULF are empty in the recorded outputs); NaN-vs-empty representation is a formatting convention — the scientific identity is "undefined for this recording per the reference method."

## Measured facts vs. open items

Measured: reference executed offline exit 0 (~8 s); all four artifacts produced; two rebuilt-environment replays byte-identical (serialization determinism on this stack only); staged input hash stable across runs; no result-bearing data files in installed distributions (dependency audit found only same-stem library source files that are required inputs to the computation, and a matplotlib test file; exclusion list empty).
Open for later validation (not resolved here): numerical tolerance calibration across implementations; whether alternative toolchains can match the preset-defined quantities within those tolerances; per-column comparison rules (which columns are robust vs. sensitive, e.g. MFDFA and entropy variants); entropy log-base if examined semantically. These do not block the scientific definition, which is fixed by the versioned preset NeuroKit2 0.2.13 with the notebook's arguments.
Note that the reference answers remain private evidence; the public task specifies the method, not the values.
