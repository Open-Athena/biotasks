#!/usr/bin/env python
"""Reference solver for the AdK domain-motion RMSD analysis task.

Reads the supplied molecular inputs and writes the five required CSV files.
"""
import argparse
import os

import pandas as pd
import MDAnalysis as mda
from MDAnalysis.analysis import rms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    psf = os.path.join(args.input_dir, "adk.psf")
    dcd = os.path.join(args.input_dir, "adk.dcd")
    crd = os.path.join(args.input_dir, "adk_open.crd")

    CORE = "backbone and (resid 1-29 or resid 60-121 or resid 160-214)"
    LID = "backbone and resid 122-159"
    NMP = "backbone and resid 30-59"

    os.makedirs(args.output_dir, exist_ok=True)

    # (1) backbone + per-domain unweighted trajectory RMSD
    u = mda.Universe(psf, dcd)
    R = rms.RMSD(u, u, select="backbone",
                 groupselections=[CORE, LID, NMP], ref_frame=0)
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ns)", "Backbone", "CORE", "LID", "NMP"]
                 ).to_csv(os.path.join(args.output_dir, "backbone_rmsd.csv"), index=False)

    # (2) CORE alpha-carbon RMSD (AtomGroup case)
    u = mda.Universe(psf, dcd)
    ca = u.select_atoms("name CA")
    R = rms.RMSD(ca, ca, select=CORE, ref_frame=0)
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ns)", "CORE"]
                 ).to_csv(os.path.join(args.output_dir, "core_ca_rmsd.csv"), index=False)

    # (3) mass-weighted RMSD (select and domain groups both mass-weighted)
    u = mda.Universe(psf, dcd)
    R = rms.RMSD(u, u, select="protein and name CA",
                 weights="mass",
                 groupselections=[CORE, LID, NMP])
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ns)", "C-alphas", "CORE", "LID", "NMP"]
                 ).to_csv(os.path.join(args.output_dir, "mass_weighted_rmsd.csv"), index=False)

    # (4) residue-number-weighted RMSD
    u = mda.Universe(psf, dcd)
    ag = u.select_atoms("protein and name CA")
    core = u.select_atoms(CORE)
    lid = u.select_atoms(LID)
    nmp = u.select_atoms(NMP)
    R = rms.RMSD(u, u, select="protein and name CA",
                 groupselections=[CORE, LID, NMP],
                 weights=ag.resids,
                 weights_groupselections=[core.resids, lid.resids, nmp.resids])
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ns)", "C-alphas", "CORE", "LID", "NMP"]
                 ).to_csv(os.path.join(args.output_dir, "resid_weighted_rmsd.csv"), index=False)

    # (5) open-vs-closed backbone RMSD (static, unweighted)
    u = mda.Universe(psf, dcd)  # fresh Universe at frame 0
    ref = mda.Universe(psf, crd)
    value = rms.rmsd(u.select_atoms("backbone").positions,
                     ref.select_atoms("backbone").positions,
                     center=True, superposition=True)
    pd.DataFrame({"backbone_rmsd_angstrom": [float(value)]}
                 ).to_csv(os.path.join(args.output_dir, "open_closed_backbone_rmsd.csv"), index=False)


if __name__ == "__main__":
    main()

