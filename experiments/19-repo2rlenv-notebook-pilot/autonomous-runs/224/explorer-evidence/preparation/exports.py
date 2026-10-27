import os as _export_os

_export_out = '/work/outputs'
_export_os.makedirs(_export_out, exist_ok=True)

df.to_csv(_export_os.path.join(_export_out, 'rmsd_calpha_core.csv'), index=False)
df_mass.to_csv(_export_os.path.join(_export_out, 'rmsd_mass_weighted.csv'), index=False)
df_charge.to_csv(_export_os.path.join(_export_out, 'rmsd_resid_weighted.csv'), index=False)