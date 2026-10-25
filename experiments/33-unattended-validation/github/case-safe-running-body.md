Build an unattended official Repo2RLEnv PR-to-task workflow with reproducible exports, independent native controls, durable evidence and owned cleanup, without per-task human/LLM repairs.

**Current:** #65’s generic case-safe staging and sealed-generation import is qualified, and its single original native validation is running against #62’s existing DendroPy export. No regeneration/model call or task/grading repair. #62 remains a preserved generation result with its original connector hold; generation billing, anonymous HF readbacks and cleanup are complete. Independent strict acceptance is still pending. [Qualified recovery and limits](https://github.com/Open-Athena/biotasks/blob/b594b049/experiments/65-sealed-case-safe-export/results.md).

**Code/findings:** draft PR #63 passes 186 local tests and both GitHub CI checks. #64’s real pytest/stdlib fixtures confirm the original/current parser gap for failing subtests; no parser change is applied. #56 provenance, #59 targeting and #60 compiled rebuilding remain separate limitations. Main and earlier PRs remain unchanged/open.

**Budget:** settled usage is **$1.723023 / 48 original calls** and **13.678994/32 CPUh**. The current native workflow reserves at most 6.333333 CPUh, projecting 20.012327 cumulative; no model reservation. Existing $10 storage reserve remains unreconciled. Same $90 operating ceiling, strictly below $100 extra, reserved CPUs only; detailed logs/accounting in comments.

Keep epic/children/PRs open for review; #28 stays closed. No automatic merge or release. Workflow completion, scientific acceptance and release readiness remain separate.
