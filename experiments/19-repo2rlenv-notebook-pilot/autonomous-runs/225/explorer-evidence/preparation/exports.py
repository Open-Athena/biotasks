import os

os.makedirs("/work/outputs", exist_ok=True)

hrv_time.to_csv("/work/outputs/hrv_time.csv", index=False)
hrv_freq.to_csv("/work/outputs/hrv_freq.csv", index=False)
hrv_nonlinear.to_csv("/work/outputs/hrv_nonlinear.csv", index=False)
hrv_indices.to_csv("/work/outputs/hrv_indices.csv", index=False)
