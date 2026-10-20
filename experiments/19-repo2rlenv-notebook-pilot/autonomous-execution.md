# Autonomous notebook pilot

`run_autonomous.py` runs one frozen notebook through conversion, terminal-export
preparation, dependency/input setup and an offline reference test, replay,
specification, construction, scientific grading controls, and native Harbor
oracle/no-op/one blind solver attempt. Scientific artifacts come exclusively from
the existing GLM workers and version-controlled prompts. All intermediate copies,
manifests, structural observations and stage dispatch are programmatic.

The existing Iris bootstrap accepts this entrypoint. Its submitted payload pins
the factory revision, notebook bytes, runtime archives and configuration. Model
and Daytona credentials remain runtime environment variables from the existing
Secret Manager launcher. Conversion uses the repository's locked environment;
remote workers retain the pinned Repo2RLEnv runtime. No notebook code runs on the
shared development VM. The entrypoint consumes `BIOTASKS_CONFIG` and
`BIOTASKS_SEED`, so changing the seed needs data/configuration, not source edits.

A single host has a two-hour campaign deadline plus the established cleanup
allowance, and at most one Daytona sandbox at a time. Each of five sandbox stages
reserves $1 before creation ($5 total); reservations are conservative allowances,
not invoices. These are within the standing $100 authorization. GLM-5.3 uses
medium reasoning; preparation has one call, other tool sessions retain their
existing finite wall-time boundaries without added byte/token/request caps.
Reference and solver computation are limited to 600 seconds, verifier to 120.
The setup worker retains two reference tests. The grading worker retains its
existing review and repair pass; no external operator supplies repair feedback.

Terminal outcomes are:

- `validated`: scientific controls accepted the candidate and native oracle/no-op
  controls passed, with a recorded blind solver attempt. Solver success is not
  required. No automatic public release is performed by this runner.
- `rejected`: an explicit worker refusal, unsupported conversion profile,
  non-repeatable outputs or recorded scientific validation failure. The receipt
  links the evidence and rejected stage; it does not label the seed bad science.
- `infrastructure_failed`: unexpected controller/provider failures, time/budget
  exhaustion, uncertain cleanup or missing evidence. This is not a successful
  rejection and does not satisfy the autonomous-run acceptance criterion.

Runs never resume in-place or overwrite prior evidence. Each stage retains its
complete receipts; final evidence is archived and downloaded for hash checking
by the existing export helper. A fresh attempt requires a new campaign identity.
If a controller defect requires a factory change, the next proof run starts from
the original seed; it cannot count a repaired stage continuation as unattended.

The first held-out case is Bioframe's `tutorial_assign_peaks_to_genes.ipynb`, pinned
at `95007ed6fc03b01005d75f95cac511b2df286854`. It has not been used for model task
generation in this project. The runner receives the notebook and general task
policy, without a manually selected analysis endpoint or task design. Input-data
redistribution is not assessed by this execution test; output remains private
unless separately approved for publication. PR 23 stays draft and unmerged until
this acceptance criterion is met and the user approves promotion.
