#!/usr/bin/env python3
"""Reference oracle: solve the public AdK RMSD task from the supplied inputs."""
import argparse
import os

import MDAnalysis as mda
from MDAnalysis.analysis import rms
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    psf = os.path.join(args.input_dir, "adk.psf")
    dcd = os.path.join(args.input_dir, "adk_dims.dcd")
    crd = os.path.join(args.input_dir, "adk_open.crd")

    CORE = "backbone and (resid 1-29 or resid 60-121 or resid 160-214)"
    LID = "backbone and resid 122-159"
    NMP = "backbone and resid 30-59"

    u = mda.Universe(psf, dcd)
    ref = mda.Universe(psf, crd)

    # 1) open vs closed backbone RMSD (trajectory frame 0 vs open CRD)
    value = float(rms.rmsd(u.select_atoms("backbone").positions,
                           ref.select_atoms("backbone").positions,
                           center=True,
                           superposition=True))
    with open(os.path.join(args.output_dir,
                           "open_closed_backbone_rmsd.csv"), "w") as fh:
        fh.write("backbone_rmsd_angstrom\n")
        fh.write(repr(value) + "\n")

    # 2) whole-trajectory backbone + domain RMSDs vs frame 0
    R = rms.RMSD(u, u, select="backbone",
                 groupselections=[CORE, LID, NMP], ref_frame=0)
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ps)", "Backbone", "CORE", "LID",
                          "NMP"]).to_csv(
        os.path.join(args.output_dir, "backbone_rmsd.csv"), index=False)

    # 3) CORE domain alpha-carbon RMSD vs frame 0
    ca = u.select_atoms("name CA")
    R = rms.RMSD(ca, ca, select=CORE, ref_frame=0)
    R.run()
    pd.DataFrame(R.results.rmsd,
                 columns=["Frame", "Time (ps)", "CORE"]).to_csv(
        os.path.join(args.output_dir, "core_ca_rmsd.csv"), index=False)

    # 4) mass-weighted RMSDs
    R_mass = rms.RMSD(u, u, select="protein and name CA", weights="mass",
                      groupselections=[CORE, LID, NMP])
    R_mass.run()
    pd.DataFrame(R_mass.results.rmsd,
                 columns=["Frame", "Time (ps)", "C-alphas", "CORE", "LID",
                          "NMP"]).to_csv(
        os.path.join(args.output_dir, "mass_weighted_rmsd.csv"), index=False)

    # 5) resid-weighted RMSDs
    ag = u.select_atoms("protein and name CA")
    core = u.select_atoms(CORE)
    lid = u.select_atoms(LID)
    nmp = u.select_atoms(NMP)
    R_resid = rms.RMSD(u, u,
                       select="protein and name CA",
                       groupselections=[CORE, LID, NMP],
                       weights=ag.resids,
                       weights_groupselections=[core.resids, lid.resids,
                                               nmp.resids])
    R_resid.run()
    pd.DataFrame(R_resid.results.rmsd,
                 columns=["Frame", "Time (ps)", "C-alphas", "CORE", "LID",
                          "NMP"]).to_csv(
        os.path.join(args.output_dir, "resid_weighted_rmsd.csv"), index=False)


if __name__ == "__main__":
    main()

