# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: nomarker
#       format_version: '1.0'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Heart Rate Variability (HRV)

# NeuroKit2 is the most comprehensive package when it comes to HRV indices, and this example shows how to use NeuroKit2 to compute heart rate variability (HRV) indices in the time-, frequency-, and non-linear domain.
#
# For a comprehensive review of the most up-to-date HRV indices, a discussion of their significance in psychology, and a step-by-step guide for HRV analysis using **NeuroKit2**, the [Heart Rate Variability in Psychology: A Review of HRV Indices and an Analysis Tutorial](https://doi.org/10.3390/s21123998) paper is a good place to start. 

# ## Compute HRV features

# Load the NeuroKit package
import neurokit2 as nk

# Note: this cell is hidden using the "remove-input" tag
# Make bigger images
import matplotlib.pyplot as plt


plt.rcParams["figure.figsize"] = [15, 5]
plt.rcParams["font.size"] = 14

# ## Download Dataset

# First, let's download the resting rate data (sampled at 100Hz) using `nk.data()`.

data = nk.data("/inputs/https/bio_resting_5min_100hz.csv")
data.head()  # Print first 5 rows

# You can see that it consists of three different signals, pertaining to ECG, PPG (an alternative determinant of heart rate as compared to ECG), and RSP (respiration). Now, let's extract the ECG signal in the shape of a vector (i.e., a one-dimensional array), and find the peaks using [ecg_peaks()](https://neuropsychology.github.io/NeuroKit/functions/ecg.html#ecg-peaks).

# Find peaks
peaks, info = nk.ecg_peaks(data["ECG"], sampling_rate=100)

# *Note: It is critical that you specify the correct sampling rate of your signal throughout many processing functions, as this allows NeuroKit to have a time reference.*

# This produces two elements, `peaks` which is a DataFrame of same length as the input signal in which occurences of R-peaks are marked with 1 in a list of zeros. `info` is a dictionary of the sample points at which these R-peaks occur. 
#
# HRV is the temporal variation between consecutive heartbeats (**RR intervals**). Here, we will use `peaks` i.e. occurrences of the heartbeat peaks, as the input argument in the following HRV functions to extract the indices. 

# ## Time-Domain Analysis

# First, let's extract the time-domain indices.

# Extract clean EDA and SCR features
hrv_time = nk.hrv_time(peaks, sampling_rate=100, show=True)
hrv_time

# These features include the RMSSD (square root of the mean of the sum of successive differences between adjacent RR intervals), MeanNN (mean of RR intervals) so on and so forth. You can also visualize the distribution of R-R intervals by specifying `show=True` in [hrv_time()](https://neuropsychology.github.io/NeuroKit/functions/hrv.html#hrv-time).

# ## Frequency-Domain Analysis

# Now, let's extract the frequency domain features, which involve extracting for example the spectral power density pertaining to different frequency bands. Again, you can visualize the power across frequency bands by specifying `show=True` in [hrv_frequency()](https://neuropsychology.github.io/NeuroKit/functions/hrv.html#hrv-frequency).

hrv_freq = nk.hrv_frequency(peaks, sampling_rate=100, show=True, normalize=True)
hrv_freq

# ## Non-Linear Domain Analysis

# Now, let's compute the non-linear indices with [hrv_nonlinear()](https://neuropsychology.github.io/NeuroKit/functions/hrv.html#hrv-nonlinear).

hrv_nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=100, show=True)
hrv_nonlinear

# This will produce a Poincaré plot which plots each RR interval against the next successive one.
#
# Note that there exist many more [**complexity indices**](https://neuropsychology.github.io/NeuroKit/functions/complexity.html), that are available in NeuroKit2, and that could be applied to HRV. The ``hrv_nonlinear()`` function only includes the most commonly used indices.

# ## All Domains

# Finally, if you'd like to extract HRV indices from all three domains, you can simply input `peaks` into [hrv()](https://neuropsychology.github.io/NeuroKit/functions/hrv.html), where you can specify `show=True` to visualize the combination of plots depicting the RR intervals distribution, power spectral density for frequency domains, and the poincare scattergram.

hrv_indices = nk.hrv(peaks, sampling_rate=100, show=True)
hrv_indices


import pathlib as _pl

_output_dir = _pl.Path("/work/outputs")
_output_dir.mkdir(parents=True, exist_ok=True)

hrv_time.to_csv(_output_dir / "hrv_time.csv", index=False)
hrv_freq.to_csv(_output_dir / "hrv_freq.csv", index=False)
hrv_nonlinear.to_csv(_output_dir / "hrv_nonlinear.csv", index=False)
hrv_indices.to_csv(_output_dir / "hrv_indices.csv", index=False)
