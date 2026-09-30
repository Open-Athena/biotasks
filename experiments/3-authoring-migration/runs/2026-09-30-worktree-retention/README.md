# Retention outside managed worktrees

The six UCSC cache files excluded from the public HF archive now have a
verified private copy outside both Codex-managed worktrees. This removes their
dependency on retaining the original authoring worktree when its chat is
archived. No chat or worktree was archived or deleted by this operation.

The [manifest](manifest.json) records the six paths, sizes, SHA-256 hashes and
retained location. The original source files and copied bytes both match the
migration allowlist: six files, 686,215 bytes. The [copy record](copy-verification.txt)
contains timing, exit status and peak RSS. File and directory permissions are
restricted to the local account.

The retained location is:

```text
/home/exedev/.local/share/biotasks/retained/3-authoring-migration/37973a95c71d5e1d38bb15c238f1d40369255359/
```

This is local storage on the same VM, outside managed worktree cleanup. It is
not an off-VM backup and was not uploaded to the public bucket. Preserve this
copy while the research depends on it. The earlier archive manifest remains
unchanged; this record adds a location and updates the retention requirement
from keeping the original worktree to keeping this verified copy.

Immediately before copying, the source head still matched
`37973a95c71d5e1d38bb15c238f1d40369255359`, the checkout was clean, and all
73 originally inventoried local files had unchanged bytes with no added or
missing files. The other 67 local files are in the anonymously verified HF
archive; tracked source research and the continuing branch are pushed to GitHub.
This accounts for the migrated authoring research, not unrelated ignored files
or environments elsewhere in the source checkout.

Later the same day, a [supplemental HF archive](../2026-09-30-ucsc-supplement/README.md)
added the README and two utility source files after file-specific license
review. Seventy of the 73 original cache files are now publicly archived;
three still depend on this separate local copy. The manifest above continues
to describe the original six-file copy operation without rewriting its history.
