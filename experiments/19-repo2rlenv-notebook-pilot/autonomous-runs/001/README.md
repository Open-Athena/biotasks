# First autonomous attempt

Factory `8ef6430002eebc0c7cfb6a949122970427a9e3d1` ran the fresh Bioframe
peaks-to-genes seed through preparation, setup and two reference replays without
operator intervention. Preparation took 172 s, setup 621 s, replay 175 s; 50 GLM
requests were recorded. No construction or solver stage ran.

The original receipt says `rejected`: the five TSV exports changed byte hashes.
A subsequent read-only audit of the original, hash-verified archived bytes found
matching headers, row counts and order-independent row-multiset signatures in
all three executions. This identifies an overly strict factory gate, not an
established scientific defect. The original receipt is unchanged, including its
stage-level `incomplete` label. The next factory version distinguishes that label
and forwards row-order observations for scientific review rather than declaring
equivalence automatically.

`replay-audit.json` records the streaming comparison; no tolerance calibration or
independent scientific reproduction is claimed. The archived biological tables
remain private. The Iris campaign and read-only audit both finished successfully;
provider cleanup found no owned Daytona sandboxes. The $2 reservation is a
conservative allowance, not a measured invoice. This attempt does not demonstrate
the complete autonomous construction/validation path.
