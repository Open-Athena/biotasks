#!/usr/bin/env python3
"""Solve the AdK RMSD task from the supplied inputs only."""
import argparse
import json
import os

import MDAnalysis as mda
from MDAnalysis.analysis import rms
import pandas as pd

CORE = ('backbone and (resid 1-29 or resid 60-121 or resid 160-214)')
LID = 'backbone and resid 122-159'
NMP = 'backbone and resid 30-59'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()
    inp = args.input_dir
    out = args.output_dir
    os.makedirs(out, exist_ok=True)

    psf = os.path.join(inp, 'structure.psf')
    dcd = os.path.join(inp, 'trajectory.dcd')
    crd = os.path.join(inp, 'reference_open.crd')

    u = mda.Universe(psf, dcd)
    u_ref_open = mda.Universe(psf, crd)

    # A. single open-vs-closed backbone RMSD (u rests at frame 0)
    a_value = rms.rmsd(u.select_atoms('backbone').positions,
                       u_ref_open.select_atoms('backbone').positions,
                       center=True, superposition=True)
    with open(os.path.join(out, 'open_closed_backbone_rmsd.json'), 'w') as fh:
        json.dump({'value': float(a_value), 'unit': 'angstrom'}, fh)
        fh.write('\n')

    # B. backbone + per-domain RMSD vs frame 0
    R = rms.RMSD(u, u, select='backbone',
                 groupselections=[CORE, LID, NMP], ref_frame=0)
    R.run()
    d = R.results.rmsd
    pd.DataFrame({
        'frame': d[:, 0].astype(int),
        'time_ps': d[:, 1],
        'backbone_rmsd_angstrom': d[:, 2],
        'core_rmsd_angstrom': d[:, 3],
        'lid_rmsd_angstrom': d[:, 4],
        'nmp_rmsd_angstrom': d[:, 5],
    }).to_csv(os.path.join(out, 'backbone_domain_rmsd.csv'), index=False)

    # C. alpha-carbon CORE RMSD vs frame 0
    ca = u.select_atoms('name CA')
    Rc = rms.RMSD(ca, ca, select=CORE, ref_frame=0)
    Rc.run()
    d = Rc.results.rmsd
    pd.DataFrame({
        'frame': d[:, 0].astype(int),
        'time_ps': d[:, 1],
        'ca_core_rmsd_angstrom': d[:, 2],
    }).to_csv(os.path.join(out, 'ca_core_rmsd.csv'), index=False)

    # D. mass-weighted RMSD
    Rm = rms.RMSD(u, u, select='protein and name CA', weights='mass',
                  groupselections=[CORE, LID, NMP])
    Rm.run()
    d = Rm.results.rmsd
    pd.DataFrame({
        'frame': d[:, 0].astype(int),
        'time_ps': d[:, 1],
        'ca_mass_weighted_rmsd_angstrom': d[:, 2],
        'core_rmsd_angstrom': d[:, 3],
        'lid_rmsd_angstrom': d[:, 4],
        'nmp_rmsd_angstrom': d[:, 5],
    }).to_csv(os.path.join(out, 'mass_weighted_rmsd.csv'), index=False)

    # E. residue-number-weighted RMSD
    ag = u.select_atoms('protein and name CA')
    core = u.select_atoms(CORE)
    lid = u.select_atoms(LID)
    nmp = u.select_atoms(NMP)
    Re = rms.RMSD(u, u, select='protein and name CA',
                  groupselections=[CORE, LID, NMP],
                  weights=ag.resids,
                  weights_groupselections=[core.resids, lid.resids, nmp.resids])
    Re.run()
    d = Re.results.rmsd
    pd.DataFrame({
        'frame': d[:, 0].astype(int),
        'time_ps': d[:, 1],
        'ca_resid_weighted_rmsd_angstrom': d[:, 2],
        'core_rmsd_angstrom': d[:, 3],
        'lid_rmsd_angstrom': d[:, 4],
        'nmp_rmsd_angstrom': d[:, 5],
    }).to_csv(os.path.join(out, 'resid_weighted_rmsd.csv'), index=False)


if __name__ == '__main__':
    main()

