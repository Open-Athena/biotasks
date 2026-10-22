# --- Export of terminal scientific results ---
# Save the existing RMSD result tables produced by the original script.
import os

_output_dir = "/work/outputs"
os.makedirs(_output_dir, exist_ok=True)

df.to_csv(os.path.join(_output_dir, "rmsd_ca_core_domain.csv"), index=False)
df_mass.to_csv(os.path.join(_output_dir, "rmsd_mass_weighted.csv"), index=False)
df_charge.to_csv(os.path.join(_output_dir, "rmsd_resid_weighted.csv"), index=False)