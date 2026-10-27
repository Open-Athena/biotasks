#!/usr/bin/env python3
"""Solve the public HRV task from the supplied inputs only.

Reads the 5-minute 100 Hz ECG/PPG/RSP recording, detects R-peaks on the raw
ECG column with NeuroKit2 0.2.13 defaults, computes all HRV indices with
nk.hrv() (which combines hrv_time, hrv_frequency and hrv_nonlinear on the
same peaks), and writes the 95 named metric columns as one CSV row.
"""
import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import neurokit2 as nk  # noqa: E402
import pandas as pd  # noqa: E402

COLUMNS = [
    # Time domain
    "HRV_MeanNN", "HRV_SDNN", "HRV_SDANN1", "HRV_SDNNI1", "HRV_SDANN2",
    "HRV_SDNNI2", "HRV_SDANN5", "HRV_SDNNI5", "HRV_RMSSD", "HRV_SDSD",
    "HRV_CVNN", "HRV_CVSD", "HRV_MedianNN", "HRV_MadNN", "HRV_MCVNN",
    "HRV_IQRNN", "HRV_SDRMSSD", "HRV_Prc20NN", "HRV_Prc80NN", "HRV_pNN50",
    "HRV_pNN20", "HRV_MinNN", "HRV_MaxNN", "HRV_HTI", "HRV_TINN",
    # Frequency domain
    "HRV_ULF", "HRV_VLF", "HRV_LF", "HRV_HF", "HRV_VHF", "HRV_TP",
    "HRV_LFHF", "HRV_LFn", "HRV_HFn", "HRV_LnHF",
    # Non-linear domain
    "HRV_SD1", "HRV_SD2", "HRV_SD1SD2", "HRV_S", "HRV_CSI", "HRV_CVI",
    "HRV_CSI_Modified", "HRV_PIP", "HRV_IALS", "HRV_PSS", "HRV_PAS",
    "HRV_GI", "HRV_SI", "HRV_AI", "HRV_PI", "HRV_C1d", "HRV_C1a",
    "HRV_SD1d", "HRV_SD1a", "HRV_C2d", "HRV_C2a", "HRV_SD2d", "HRV_SD2a",
    "HRV_Cd", "HRV_Ca", "HRV_SDNNd", "HRV_SDNNa", "HRV_DFA_alpha1",
    "HRV_MFDFA_alpha1_Width", "HRV_MFDFA_alpha1_Peak",
    "HRV_MFDFA_alpha1_Mean", "HRV_MFDFA_alpha1_Max",
    "HRV_MFDFA_alpha1_Delta", "HRV_MFDFA_alpha1_Asymmetry",
    "HRV_MFDFA_alpha1_Fluctuation", "HRV_MFDFA_alpha1_Increment",
    "HRV_DFA_alpha2",
    "HRV_MFDFA_alpha2_Width", "HRV_MFDFA_alpha2_Peak",
    "HRV_MFDFA_alpha2_Mean", "HRV_MFDFA_alpha2_Max",
    "HRV_MFDFA_alpha2_Delta", "HRV_MFDFA_alpha2_Asymmetry",
    "HRV_MFDFA_alpha2_Fluctuation", "HRV_MFDFA_alpha2_Increment",
    "HRV_ApEn", "HRV_SampEn", "HRV_ShanEn", "HRV_FuzzyEn", "HRV_MSEn",
    "HRV_CMSEn", "HRV_RCMSEn", "HRV_CD", "HRV_HFD", "HRV_KFD", "HRV_LZC",
    "HRV_Symbolic_EqualProb4_0V", "HRV_Symbolic_EqualProb4_1V",
    "HRV_Symbolic_EqualProb4_2LV", "HRV_Symbolic_EqualProb4_2UV",
]

INPUT_NAME = "bio_resting_5min_100hz.csv"
OUTPUT_NAME = "hrv_indices.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(input_dir / INPUT_NAME)
    ecg = data["ECG"]

    # Step 1: R-peak detection on the raw ECG column (NeuroKit2 0.2.13
    # defaults: method="neurokit", correct_artifacts=False), 100 Hz.
    peaks, info = nk.ecg_peaks(ecg, sampling_rate=100)

    # Step 2: all-domain HRV from the same peak series at 100 Hz. nk.hrv()
    # combines hrv_time, hrv_frequency (normalize default) and hrv_nonlinear.
    # show only controls plotting, so it is disabled here.
    hrv = nk.hrv(peaks, sampling_rate=100, show=False)

    missing = [column for column in COLUMNS if column not in hrv.columns]
    if missing:
        raise SystemExit("missing expected HRV columns: %r" % missing)

    result = hrv[COLUMNS].copy()
    result.to_csv(output_dir / OUTPUT_NAME, index=False)


if __name__ == "__main__":
    main()

