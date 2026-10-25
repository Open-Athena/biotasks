#!/usr/bin/env python3
"""Oracle: HRV indices of a 5-minute resting ECG recording (NeuroKit2 0.2.13).

Faithful rerun of the source notebook's computation on the supplied input:
raw ECG -> nk.ecg_peaks (default neurokit method, no artifact correction) ->
nk.hrv_time / nk.hrv_frequency(normalize=True) / nk.hrv_nonlinear / nk.hrv,
all at sampling_rate=100. Uses only the supplied inputs directory.
"""
import argparse
import os

# Ensure no display is required (plots are not requested; show defaults False).
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    import neurokit2 as nk

    input_csv = os.path.join(args.input_dir, "bio_resting_5min_100hz.csv")
    data = pd.read_csv(input_csv)

    # R-peak detection on the raw ECG at 100 Hz (default "neurokit" method,
    # correct_artifacts=False).
    peaks, _info = nk.ecg_peaks(data["ECG"], sampling_rate=100)

    out = {}
    out["hrv_time"] = nk.hrv_time(peaks, sampling_rate=100)
    out["hrv_freq"] = nk.hrv_frequency(peaks, sampling_rate=100, normalize=True)
    out["hrv_nonlinear"] = nk.hrv_nonlinear(peaks, sampling_rate=100)
    out["hrv_indices"] = nk.hrv(peaks, sampling_rate=100)

    os.makedirs(args.output_dir, exist_ok=True)
    for name, df in out.items():
        df.to_csv(os.path.join(args.output_dir, name + ".csv"), index=False)


if __name__ == "__main__":
    main()

