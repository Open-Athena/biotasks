#!/usr/bin/env python3
"""Reference solution for the AdK open<->closed RMSD task.

Solves the public task using only the supplied inputs/ directory and writes
the five required CSV tables to the given output directory.
"""
import argparse
import os

import MDAnalysis as mda
import pandas as pd
from MDAnalysis.analysis import rms

CORE = 'backbone and (resid 1-29 or resid 60-121 or resid 160-214)'
LID = 'backbone and resid 122-159'
NMP = 'backbone and resid 30-59'


def main():
    ap = argparse.ArgumentParser(description="AdK RMSD analyses A-E")
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    psf = os.path.join(args.input_dir, 'adk.psf')
    dcd = os.path.join(args.input_dir, 'adk_trajectory.dcd')
    crd = os.path.join(args.input_dir, 'adk_open.crd')
    os.makedirs(args.output_dir, exist_ok=True)

    u = mda.Universe(psf, dcd)        # trajectory (frame 0 = closed)
    ref_open = mda.Universe(psf, crd)  # open conformation

    # ---- A. Open vs closed endpoint backbone RMSD ----------------------
    a_value = float(rms.rmsd(u.select_atoms('backbone').positions,
                             ref_open.select_atoms('backbone').positions,
                             center=True,
                             superposition=True))
    pd.DataFrame({'rmsd_backbone_angstrom': [a_value]}).to_csv(
        os.path.join(args.output_dir, 'rmsd_backbone_open_closed.csv'),
        index=False)

    # ---- B. Backbone fit, CORE/LID/NMP residual group RMSDs -------------
    R = rms.RMSD(u, u,
                 select='backbone',
                 groupselections=[CORE, LID, NMP],
                 ref_frame=0)
    R.run()
    b = R.results.rmsd
    pd.DataFrame({'frame': b[:, 0].astype(int),
                  'rmsd_backbone_angstrom': b[:, 2],
                  'rmsd_core_angstrom': b[:, 3],
                  'rmsd_lid_angstrom': b[:, 4],
                  'rmsd_nmp_angstrom': b[:, 5]}).to_csv(
        os.path.join(args.output_dir, 'rmsd_backbone_domains.csv'),
        index=False)

    # ---- C. CORE restricted to alpha-carbons ----------------------------
    ca = u.select_atoms('name CA')
    Rc = rms.RMSD(ca, ca, select=CORE, ref_frame=0)
    Rc.run()
    c = Rc.results.rmsd
    pd.DataFrame({'frame': c[:, 0].astype(int),
                  'rmsd_core_ca_angstrom': c[:, 2]}).to_csv(
        os.path.join(args.output_dir, 'rmsd_ca_core.csv'),
        index=False)

    # ---- D. Mass-weighted ------------------------------------------------
    Rd = rms.RMSD(u, u,
                  select='protein and name CA',
                  weights='mass',
                  groupselections=[CORE, LID, NMP])
    Rd.run()
    d = Rd.results.rmsd
    pd.DataFrame({'frame': d[:, 0].astype(int),
                  'rmsd_ca_mass_angstrom': d[:, 2],
                  'rmsd_core_mass_angstrom': d[:, 3],
                  'rmsd_lid_mass_angstrom': d[:, 4],
                  'rmsd_nmp_mass_angstrom': d[:, 5]}).to_csv(
        os.path.join(args.output_dir, 'rmsd_mass_weighted.csv'),
        index=False)

    # ---- E. Residue-number-weighted ---------------------------------------
    ag = u.select_atoms('protein and name CA')
    core = u.select_atoms(CORE)
    lid = u.select_atoms(LID)
    nmp = u.select_atoms(NMP)
    Re = rms.RMSD(u, u,
                  select='protein and name CA',
                  groupselections=[CORE, LID, NMP],
                  weights=ag.resids,
                  weights_groupselections=[core.resids,
                                           lid.resids,
                                           nmp.resids])
    Re.run()
    e = Re.results.rmsd
    pd.DataFrame({'frame': e[:, 0].astype(int),
                  'rmsd_ca_resid_angstrom': e[:, 2],
                  'rmsd_core_resid_angstrom': e[:, 3],
                  'rmsd_lid_resid_angstrom': e[:, 4],
                  'rmsd_nmp_resid_angstrom': e[:, 5]}).to_csv(
        os.path.join(args.output_dir, 'rmsd_resid_weighted.csv'),
        index=False)


if __name__ == '__main__':
    main()
