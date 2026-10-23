import os as _os

_export_dir = "/work/outputs"
_os.makedirs(_export_dir, exist_ok=True)

df.to_csv(_os.path.join(_export_dir, "ca_core_rmsd.csv"), index=False)
df_mass.to_csv(_os.path.join(_export_dir, "mass_weighted_rmsd.csv"), index=False)
df_charge.to_csv(_os.path.join(_export_dir, "resid_weighted_rmsd.csv"), index=False)