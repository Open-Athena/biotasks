import argparse
import os

import matplotlib

matplotlib.use("Agg")

import neurokit2 as nk  # noqa: E402
import pandas as pd  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Compute HRV indices (time, frequency, nonlinear, combined) from a 5-min rest ECG."
    )
    parser.add_argument("--input-dir", required=True,
                        help="Directory containing bio_resting_5min_100hz.csv")
    parser.add_argument("--output-dir", required=True,
                        help="Directory to write the four HRV CSV tables into")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)

    data = pd.read_csv(os.path.join(args.input_dir, "bio_resting_5min_100hz.csv"))
    ecg = data["ECG"]

    # R-peak detection on the raw (uncleaned) ECG, default "neurokit" method,
    # no artifact correction, sampling rate 100 Hz.
    peaks, info = nk.ecg_peaks(ecg, sampling_rate=100)

    hrv_time = nk.hrv_time(peaks, sampling_rate=100)
    hrv_freq = nk.hrv_frequency(peaks, sampling_rate=100, normalize=True)
    hrv_nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=100)
    hrv_indices = nk.hrv(peaks, sampling_rate=100)

    hrv_time.to_csv(os.path.join(args.output_dir, "hrv_time.csv"), index=False)
    hrv_freq.to_csv(os.path.join(args.output_dir, "hrv_frequency.csv"), index=False)
    hrv_nonlinear.to_csv(os.path.join(args.output_dir, "hrv_nonlinear.csv"), index=False)
    hrv_indices.to_csv(os.path.join(args.output_dir, "hrv_indices.csv"), index=False)

    print("wrote hrv_time.csv, hrv_frequency.csv, hrv_nonlinear.csv, hrv_indices.csv")


if __name__ == "__main__":
    main()

