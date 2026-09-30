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
