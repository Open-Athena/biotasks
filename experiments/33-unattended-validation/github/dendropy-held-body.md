Build an unattended official Repo2RLEnv PR-to-task workflow with reproducible exports, independent native controls, durable evidence and owned cleanup, without per-task human/LLM repairs.

**Latest result:** #62 generated one fresh DendroPy export, but our local inline handoff stopped at mixed-case cache/lowercase image-tag matching before controls. Generation billing, both anonymous HF readbacks and owned cleanup are verified; original controller is terminal. No accepted fresh task/control pair. #53/#57/#58 retain earlier zero-export/collection failures; #61’s known Cobrapy export was deferred before execution. [Latest diagnosis](https://github.com/Open-Athena/biotasks/blob/832671b9/experiments/62-fresh-dendropy/cache-case-diagnosis.json).

**Next:** #65 qualifies generic cache matching and read-only import of sealed generations so controls can reuse #62 without model calls or regeneration. #64 records a native subtest-parser gap. #56 provenance, #59 targeting limits and #60 compiled rebuilding remain separate; none is silently applied. No new native/model admission yet.

**Code/budget:** consolidated draft PR #63 passes 167 local tests and both GitHub CI checks; main and earlier PRs remain unchanged/open. Settled incremental usage is **$1.723023 / 48 original calls** and **13.678994/32 allocated CPUh**, no native/model reservations; existing $10 storage reserve remains unreconciled. Same $90 operating ceiling, strictly below $100 extra, reserved CPUs only. Detailed logs/accounting in comments.

Keep epic/children/PRs open for review; #28 stays closed. No automatic merge or release. Workflow completion, scientific acceptance and release readiness remain separate.
