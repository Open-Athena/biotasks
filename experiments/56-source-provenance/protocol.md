# Python project source provenance

Actual child #56 of #33, permanent research branch from recorded main2a1950d2.
First inspect the pinned official bootstrap/validation/cache implementation and
existing instrumentation. Reuse original #53 evidence; no input rerun or repair.

Original #53: 9 official model calls/$0.313983, zero exports. Backport #2710 was
filtered; #2641 completed both changed-file suites in206seconds with the same
two failures/1536passes. Both traces retain the old index guard under site-packages
after the worktree patch applied cleanly. Original full-suite300second bootstrap
checks timed out separately; the native validation did not time out. These
observations do not prove an unsuitable PR or identify the exact installed
distribution version/realpath.

Hypothesis: editable version0.0.0 plus a later companion/test dependency install
allows replacement with a release. That exact transaction is not retained. A
generic check must resolve realpaths and distribution/direct_url metadata, not
declare every site-packages path invalid. Account for editable forwarding,
symlinks, namespace ambiguity, copied/rebuilt code and project/import-name
differences. Unknown provenance remains explicit, never an invented success.

Initial source/offline scope, zero native/model calls or new budget allowance.
Design and test the provenance representation on small real local package
fixtures; clearly label them synthetic and separate from original AnnData
evidence. Use the locked Python/uv tools, bounded local resources and heavy-work
lock for substantive fixture installs/tests; keep all scratch under this
experiment and clean it after retained hashes/reports.

Do not set PYTHONPATH or change install/test/source/grading/timeout for #53.
No extra LLM/Codex/solver repair stage. Any runtime/prompt/tool candidate must
have a concrete justified diff and separately frozen comparison before use;
do not present it as the unmodified baseline. No native comparison admitted
here. Same epic32CPUh/90USDoperating ceiling, strictly below100USDextra; no new
capacity. Original #53 controller finishes unchanged archival/cleanup. Keep
issues/PRs open for review; no automatic merge or release.
