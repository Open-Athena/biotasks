# Task-authoring research logbook

## 2026-09-30 — continuing study created

[Research issue #10](https://github.com/Open-Athena/biotasks/issues/10) separates
the open scientific question from [migration #3](https://github.com/Open-Athena/biotasks/issues/3).
The branch carries the original migration commits, starting from recorded
`main` commit `37271415c4c201ba9dbbda66c203caa4050744c3`. It branches from
preservation/archive checkpoint `046056ec94b602782a33f1172c8598fc7df29df3`.
The source migration branch remains published and retained.

The [migration logbook](../3-authoring-migration/logbook.md) records the source
head, complete path accounting, promotion decisions, failed checker attempt
and corrected verification. All 487 source files and 37 run records are
preserved. The public archive was verified anonymously; six UCSC files remain
explicitly at source, including two local-only mutable-source captures. No
source cache or source branch was deleted.

The next scientific work needs a separately recorded question and budget.
Useful directions include completion/source-fidelity comparisons and actual
authoring trials with native references and independent validation. None is
launched by this handoff. Candidate prompt improvements are deferred; the
separate reconciliation stage is not adopted. No scientific prompt promotion,
PR or merge is claimed.

## 2026-09-30 — prepare the old chat for archival

The user asked whether the original authoring chat could be archived, which
can delete its managed worktree. The source checkout and all 73 local evidence
files were unchanged. Copied and verified the six HF-excluded UCSC files into
private storage outside managed worktrees; see the
[retention record](../3-authoring-migration/runs/2026-09-30-worktree-retention/README.md).
The other evidence is already on GitHub or in the verified public HF archive.
This preserves the migrated research through source-worktree removal without
redistributing the excluded source bytes. No chat or worktree was archived here.

## 2026-09-30 — correct the blanket UCSC exclusion

The user challenged the exclusion of all UCSC files from HF. A file-specific
review confirmed the root README's default license and the explicit MIT
license for the two cached utility sources. The blanket hold was too broad.
A [supplemental archive](../3-authoring-migration/runs/2026-09-30-ucsc-supplement/README.md)
now preserves these three original files with their exact upstream notices.
Both objects and all seven archive members matched after anonymous download.
The original snapshot and manifests remain unchanged.

Public HF snapshots now contain 70 of the 73 original cache files. The liftOver
source and two mixed directory/help captures remain in verified private storage
outside managed worktrees. Public redistribution of those complete files was
not established; this is not a blanket claim that UCSC or non-commercial
material cannot be archived on HF. The local copy protects the migrated evidence
from old-worktree removal, but not loss of the VM. No chat or worktree was
archived or deleted.

## 2026-09-30 — complete public cache archival

The user explicitly requested archival of the three remaining UCSC files.
The [final snapshot](../3-authoring-migration/runs/2026-09-30-ucsc-remaining/README.md)
preserves those exact bytes with upstream notices and source provenance,
without changing their terms. Its manifest was pushed before transfer. The
first attempt stopped at the shared-node lock before starting a worker; a
subsequent guarded transfer succeeded and all objects/members matched after
anonymous download.

Combined verification across the three snapshots accounts for all 73
original cache files (8,912,921 bytes), with no missing or duplicate originals.
None remains local-only. All earlier snapshots and local copies remain
intact. The migrated evidence no longer depends on retaining the old managed
worktree. No chat or worktree was archived or deleted here, and no scientific
run or prompt promotion was performed.

## 2026-10-06 — final issue handoff

The migration and archival work is complete. Issue #10's handoff is updated
to the final three-snapshot archive rather than the initial six-file exclusion.
The migration and continuing-study entry points now link complete archival
and coverage evidence. Original dated records and snapshot manifests remain
unchanged. The publication receipts record September 30 verification; this
documentation handoff does not claim a fresh download or scientific run.

Migration #3 is closed. Research #10 remains open for source-fidelity and
completion comparisons, followed by authoring trials with native references
and independent validation. A future worker can start from the published
research branch and linked immutable evidence without either previous chat
or its worktree. Before execution, select a question and comparison criteria,
record exact inputs and budget, and obtain the applicable execution
authorization. No model calls, paid compute or concurrent agents are launched
or authorized by this wrap-up.

## 2026-10-06 — research conclusion

The user clarified that this research study should conclude with its current
findings and next steps, rather than remain open for hypothetical future work.
This supersedes the earlier same-day plan to keep #10 open. The study is
concluded without promoting candidate prompts or claiming validated task
authoring. No new experiment was performed for closure.

### Conclusions

- Source inventories can expose useful operations and candidate task inputs,
  but the saved trials do not demonstrate reliable source fidelity or complete
  coverage. Structural validity and worker readiness claims missed scientific
  and metadata errors; independent source-backed review remains necessary.
- Retain a single explorer as the research starting point. Reject a separate
  reconciliation worker as an active pipeline stage: the trials repaired some
  identities but left semantic defects, without demonstrated equal-cost or
  downstream authoring benefit. This is not a general proof that reconciliation
  cannot help.
- Retain access fallbacks, inspection queues, identity/processing-state checks
  and operation-level catalog accounting as candidates. Do not promote the
  bundled prompt changes: gains were mixed, repeated results unstable, and
  clause-specific contributions were not isolated. The UCSC catalog accounted
  for 328 entries but left 283 pending; removing artificial caps did not establish
  reliable completion.
- Do not select a default model or reasoning effort from the DESeq2 matrix:
  three cells completed, one was service-blocked, with one run per cell and
  unknown served settings/billed cost. Infrastructure failures remain separate
  from scientific outcomes.
- The authoring template remains untested. There is no demonstrated new
  independently validated task, maintained solve/reflection orchestration or
  portable generator from this study. Preserve historical helpers as evidence,
  not maintained runtime code.
- No supported pipeline change or promotion PR is warranted from the current
  evidence. The [candidate decision table](../3-authoring-migration/logbook.md#candidate-decisions)
  records each disposition and its decisive evidence. The 37 run records,
  487 original tracked files and all 73 local cache files remain preserved.

### Possible follow-up studies

1. Measure source fidelity and completion on fixed inputs across repository
   types, with withheld source-backed criteria, repeated trials and comparable
   execution budgets. Isolate prompt changes instead of attributing bundled
   gains to individual clauses.
2. Trial focused and connected task authoring from independently audited
   inventories, using observed data, native references, deterministic artifact
   grading, meaningful incorrect submissions and independent solving.
3. Promote only changes supported by those comparisons through a fresh focused
   branch from current main. Keep source ranking in #5; any new research issue
   should record its own hypothesis, baseline, scope and execution budget.

These are optional next studies, not outstanding work required to close #10.
They are not launched or funded by closure. Retain the published research
branch and all three HF snapshots; closing the issue does not delete evidence
from GitHub, HF or local storage.
