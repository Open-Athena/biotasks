import os as _os
_os.makedirs('/work/outputs', exist_ok=True)

df.to_csv('/work/outputs/core_ca_rmsd.csv', index=False)
df_mass.to_csv('/work/outputs/mass_weighted_rmsd.csv', index=False)
df_charge.to_csv('/work/outputs/resid_weighted_rmsd.csv', index=False)
