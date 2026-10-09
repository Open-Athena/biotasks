# Factory batch004 execution report

All ten seed jobs are terminal. Nine proposals passed their interface check and entered construction, up from three in batch003. Eight candidates failed native static checks, but a missing candidate hash prevented the controller from routing these failures to GLM review. One construction produced no task directory and failed restoration; one proposal had invalid evidence paths. Accepted-task yield is 0/10, with zero native trials and zero solver attempts. These outcomes do not establish scientific unsuitability.

The frozen factory was `98107d6f752f4dd25454c3d25d127f7d5abdc2fa`; see the [batch](factory-batch-004.json), [budget](factory-batch-004-budget.json) and [terminal observation](factory-batch-004-terminal-observation.json). Inputs and seed choices were unchanged. Historical manually supervised outcomes are excluded.

| Seed | Specification requests | Construction requests | Recorded worker seconds, summed | Disposition |
| --- | ---: | ---: | ---: | --- |
| bedtools | 11 | 0 | 42.8 | proposal_contract_failure |
| cobrapy | 7 | 54 | 243.3 | static_defect_routing_failure |
| mdanalysis | 8 | 35 | 256.4 | static_defect_routing_failure |
| methylkit | 7 | 60 | 347.3 | static_defect_routing_failure |
| phyloseq | 9 | 41 | 261.7 | static_defect_routing_failure |
| pyradiomics | 7 | 60 | 370.8 | static_defect_routing_failure |
| qfeatures | 8 | 60 | 477.9 | empty_construction |
| scanpy | 8 | 60 | 472.5 | static_defect_routing_failure |
| skbio | 6 | 60 | 353.1 | static_defect_routing_failure |
| xcms | 11 | 60 | 801.1 | static_defect_routing_failure |

The run recorded 572 authoring requests. Usage was present for 571/572, totaling 24,848,946 provider-reported input tokens and 327,644 output tokens. These are reported token counts, not uncached-token billing estimates; no measured orchestration cost or provider invoice is available. Worker seconds exclude queueing, staging and native setup and are not solver runtimes.

Native static errors concern Harbor schema/solver configuration (two candidates), separate verifier configuration (one), or missing validation assets (five). All eight native summaries explicitly contain zero cases. QFeatures stopped before native-suite invocation because no task directory was present; bedtools stopped during proposal validation. Neither task correctness nor solver performance was measured.

The subsequent factory adds a read-only interface checker to bounded GLM stages, retains candidate identity on static failures, and lets a checksum-verified empty construction reach GLM review. Baselines still require a task. No generated scientific content or package was manually edited; those changes require a fresh frozen panel to validate.

The [first recovery](factory-batch-004-recovery-001.json) failed because its compressed export exceeded the transport bound. The [second recovery](factory-batch-004-recovery-002.json) omitted verbose traces and recovered 355 text artifacts with a verified export checksum. Large and binary artifacts remain in durable storage. Both recovery jobs are terminal; this is not a complete portable release.

The [explorer manifest](factory-batch-004-campaign.json) exposes ten factory stage histories and the preserved worker statistics. Candidate bodies and complete authoring traces are not embedded in this summary view. No solver score or attempt is displayed because none exists. Accepted-task inspection remains an unfinished deliverable.
