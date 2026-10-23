#!/usr/bin/env python
"""Reference solution: AdK closed->open RMSD analyses A-E.

Uses only the supplied inputs under --input-dir; writes the five required
CSVs to --output-dir.
"""
import argparse
import os

import pandas as pd
import MDAnalysis as mda
from MDAnalysis.analysis import rms

CORE = 'backbone and (resid 1-29 or resid 60-121 or resid 160-214)'
LID = 'backbone and resid 122-159'
NMP = 'backbone and resid 30-59'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    base = os.path.join(args.input_dir, 'mdanalysis-rmsd')
    psf = os.path.join(base, 'adk.psf')
    dcd = os.path.join(base, 'adk_dims.dcd')
    crd = os.path.join(base, 'adk_open.crd')
    out = args.output_dir
    os.makedirs(out, exist_ok=True)

    # ---- A: open-vs-closed backbone RMSD (single value) ----
    # Trajectory universe freshly loaded, positioned at frame 0.
    u = mda.Universe(psf, dcd)
    ref = mda.Universe(psf, crd)
    oc = rms.rmsd(u.select_atoms('backbone').positions,
                  ref.select_atoms('backbone').positions,
                  center=True, superposition=True)
    pd.DataFrame({'Backbone': [float(oc)]}).to_csv(
        os.path.join(out, 'open_closed_backbone_rmsd.csv'), index=False)

    # ---- B: backbone-referenced trajectory RMSDs ----
    u = mda.Universe(psf, dcd)
    R = rms.RMSD(u, u, select='backbone',
                 groupselections=[CORE, LID, NMP], ref_frame=0)
    R.run()
    a = R.results.rmsd
    pd.DataFrame({'Frame': a[:, 0].astype(int),
                  'Backbone': a[:, 2],
                  'CORE': a[:, 3],
                  'LID': a[:, 4],
                  'NMP': a[:, 5]}
                 ).to_csv(os.path.join(out, 'backbone_rmsd.csv'), index=False)

    # ---- C: alpha-carbon CORE RMSD ----
    u = mda.Universe(psf, dcd)
    ca = u.select_atoms('name CA')
    R = rms.RMSD(ca, ca, select=CORE, ref_frame=0)
    R.run()
    a = R.results.rmsd
    pd.DataFrame({'Frame': a[:, 0].astype(int),
                  'CORE': a[:, 2]}
                 ).to_csv(os.path.join(out, 'ca_core_rmsd.csv'), index=False)

    # ---- D: mass-weighted branch ----
    u = mda.Universe(psf, dcd)
    Rm = rms.RMSD(u, u,
                  select='protein and name CA',
                  weights='mass',
                  groupselections=[CORE, LID, NMP])
    Rm.run()
    a = Rm.results.rmsd
    pd.DataFrame({'Frame': a[:, 0].astype(int),
                  'C-alphas': a[:, 2],
                  'CORE': a[:, 3],
                  'LID': a[:, 4],
                  'NMP': a[:, 5]}
                 ).to_csv(os.path.join(out, 'mass_weighted_rmsd.csv'),
                          index=False)

    # ---- E: residue-number-weighted branch ----
    u = mda.Universe(psf, dcd)
    ag = u.select_atoms('protein and name CA')
    core = u.select_atoms(CORE)
    lid = u.select_atoms(LID)
    nmp = u.select_atoms(NMP)
    Rr = rms.RMSD(u, u,
                  select='protein and name CA',
                  groupselections=[CORE, LID, NMP],
                  weights=ag.resids,
                  weights_groupselections=[core.resids, lid.resids,
                                           nmp.resids])
    Rr.run()
    a = Rr.results.rmsd
    pd.DataFrame({'Frame': a[:, 0].astype(int),
                  'C-alphas': a[:, 2],
                  'CORE': a[:, 3],
                  'LID': a[:, 4],
                  'NMP': a[:, 5]}
                 ).to_csv(os.path.join(out, 'resid_weighted_rmsd.csv'),
                          index=False)

    print('oracle complete: %s' % out)


if __name__ == '__main__':
    main()

