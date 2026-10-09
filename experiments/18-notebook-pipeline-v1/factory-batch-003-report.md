# Factory batch003 execution report

All ten seed jobs are terminal. Three proposals passed the interface check and entered construction; seven stopped at proposal-format checks. No candidate reached native trials because the native worker could not import a restored helper. Accepted-task yield is 0/10, with zero baseline solver attempts. These are factory/interface outcomes, not evidence that the notebooks are scientifically unsuitable.

The factory-only run used revision `f490aa3bac8ffad47de3b547e1f05f56d425661d`; its exact configuration and finite budget are in [the batch](factory-batch-003.json) and [budget](factory-batch-003-budget.json). Original source pins and inputs remained unchanged. Historical manually supervised successes are excluded.

| Seed | Specification requests | Construction requests | Recorded worker seconds, summed | Disposition |
| --- | ---: | ---: | ---: | --- |
| bedtools | 5 | 60 | 217.8 | native_setup_failure |
| cobrapy | 7 | 0 | 28.3 | proposal_contract_failure |
| mdanalysis | 8 | 0 | 39.6 | proposal_contract_failure |
| methylkit | 9 | 0 | 46.0 | proposal_contract_failure |
| phyloseq | 8 | 0 | 41.2 | proposal_contract_failure |
| pyradiomics | 7 | 0 | 34.6 | proposal_contract_failure |
| qfeatures | 8 | 0 | 56.8 | proposal_contract_failure |
| scanpy | 7 | 57 | 519.2 | native_setup_failure |
| skbio | 7 | 60 | 303.2 | native_setup_failure |
| xcms | 12 | 0 | 50.8 | proposal_contract_failure |

The run recorded 255 authoring requests. Provider usage was present for 255/255 requests, totaling 9,813,099 reported input tokens and 136,307 reported output tokens. These are API-reported counts, not uncached-token billing estimates. The existing inference service was used; no provider invoice or measured orchestration cost is available. Worker seconds sum the completed authoring stages for each seed; they exclude queueing, staging and orchestration and are not reference or solver runtimes. Resource snapshots are retained per worker and exposed in the explorer.

Six proposals used an object for `reference_ecosystem` where the controller required a string; MDAnalysis had the same type and also omitted `evidence_paths`, which stopped validation first. The prompt did not clearly state all field types. Bedtools and scikit-bio reached their 60-request construction cap; Scanpy finished normally after 57 requests. All three native workers then failed before trials with `ModuleNotFoundError: No module named 'restore_authoring'`. No scientific grade can be inferred from these failures.

The next factory revision clarifies the shared proposal interface and launches the native worker from the directory holding its restored helpers. A subprocess regression covers that import boundary. Generated proposals, task science, packaging and graders were not manually repaired. The corrections need another frozen execution panel; local tests alone do not establish end-to-end success.

The [terminal observation](factory-batch-003-terminal-observation.json), [first recovery receipt](factory-batch-003-recovery-001.json) and [second recovery receipt](factory-batch-003-recovery-002.json) preserve the outcome and recovery limits. Full artifacts remain in private durable storage. The bounded text recovery excludes large/binary files and records omissions; it is not a complete portable dataset release.

The [factory-only explorer manifest](factory-batch-003-campaign.json) reuses the notebook/task/attempt viewer with ten stage histories and recorded worker resource/token summaries. No solver trace or score is shown because none exists for this panel. Candidate bodies and full authoring traces are not embedded in this public summary view. The explorer remains an incomplete issue deliverable until accepted tasks and their attempts can be inspected.
