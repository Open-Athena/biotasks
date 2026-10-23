import os

import pandas as _pd

_out_dir = "/work/outputs"
os.makedirs(_out_dir, exist_ok=True)

# Save the terminal HRV results produced by the original script.
hrv_time.to_csv(os.path.join(_out_dir, "hrv_time.csv"), index=False)
hrv_freq.to_csv(os.path.join(_out_dir, "hrv_frequency.csv"), index=False)
hrv_nonlinear.to_csv(os.path.join(_out_dir, "hrv_nonlinear.csv"), index=False)
hrv_indices.to_csv(os.path.join(_out_dir, "hrv_indices.csv"), index=False)