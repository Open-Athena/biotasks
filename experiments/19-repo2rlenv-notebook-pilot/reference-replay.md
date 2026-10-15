# Frozen reference repeatability check

This is the first executable validation step after specification 013. It makes
**zero model calls** and does not generate a task or grading rules. Its inputs
are the accepted preparation and successful setup snapshot, selected by the
[configuration](reference-replay.json). The public task brief does not control
scientific execution.

The controller verifies the snapshot's file hashes, links its original source,
exports and inventory to preparation, and checks the assembled reference script.
It creates one fresh CPU-only Daytona sandbox through the existing setup runner.
It installs the generated project with the **saved uv lock**, without running a
new resolution, and verifies the resulting package list and lock against the
original records. The saved staging recipe fetches the original inputs; their
recorded SHA-256 hashes must match before and after every reference run.

Two fresh reference processes run sequentially, with empty working/output
folders, offline, and with the original 600-second limit each. They share the
rebuilt environment and caches. Both preserve all original computation and
selected exports. No setup or scientific repair runs automatically. Failures
retain evidence and stop this check.

The report compares every declared output's SHA-256 against the original run
and the preceding fresh run. It preserves complete output files in the artifact
store and only small results/manifests in Git. Byte equality is an observation,
**not the future grading rule**. Differences require subsequent semantic
inspection; the controller neither invents tolerances nor changes the outputs.
Two repeats are an initial variability probe, not statistical calibration or a
cross-platform reproducibility guarantee. The original versioned base-image tag
is reused; its immutable image digest was not recorded in setup 001.

Execution uses the already agreed 4 CPUs, 8 GiB RAM and 10 GiB disk, no GPU,
30-minute setup allowance and two-hour campaign with cleanup. A $2 conservative
reservation stays inside the existing $100 authorization. This reserves money,
not a measured provider charge. The Iris host receives only the Daytona
credential; replay neither needs nor receives a GLM credential or model route.

After reviewing these observations, the next worker can construct a public
acceptance contract and grader using the reference artifacts and validation
handoff. That worker must justify any permitted numerical or representation
variation, and exercise reference, no-op, missing-endpoint and meaningful wrong
outputs. Solver attempts, publication and viewer updates are separate.
