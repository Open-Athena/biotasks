import pathlib as _pl

_output_dir = _pl.Path("/work/outputs")
_output_dir.mkdir(parents=True, exist_ok=True)

hrv_time.to_csv(_output_dir / "hrv_time.csv", index=False)
hrv_freq.to_csv(_output_dir / "hrv_freq.csv", index=False)
hrv_nonlinear.to_csv(_output_dir / "hrv_nonlinear.csv", index=False)
hrv_indices.to_csv(_output_dir / "hrv_indices.csv", index=False)
