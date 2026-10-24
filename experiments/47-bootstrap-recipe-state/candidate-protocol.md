# Candidate contract: apt-index-refresh-v1

This is an explicitly changed experimental emitter, not an unchanged official
pipeline result. Its justification is the source-bound package-index lifetime
failure. There is no repository, package-name or PR-specific branch, inferred
dependency, model call, task edit or additional generation attempt.

The adapter temporarily wraps the pinned `_build_clean_recipe` in memory. It
deep-copies data, normalizes supported saved commands, then calls the original
renderer with all other fields unchanged. Original source/cache/raw files are
never overwritten. A changed recipe receives an experimental policy comment;
the original exporter itself computes its hash/line metadata. Context exit
restores the original renderer, including on interruption. Policy and adapter
code hashes belong in the local handoff configuration identity before execution.

Supported APT forms are literal `apt-get install` with the listed quiet/yes and
no-recommends/suggests options plus literal package/version arguments, a simple
`apt-get update`, or one `update && install` pair. A bare install is prefixed
with `apt-get update &&`; an already refreshed pair/update is preserved. No
packages are added, dropped, renamed or version-adjusted. No-APT commands and
renderings remain byte-identical. Shell operators, expansions, pipes, masking,
sudo/apt wrappers, unsupported options and multiline forms are explicitly
unsupported when literal APT syntax is detected. This limited recognizer is not
a complete shell parser or general dependency-closure guarantee.

Meaningful checks include a fake APT executable with initially missing indexes:
the original install fails100, the candidate updates then installs, and a failed
update exits7 without attempting install. Other checks cover unsupported syntax,
preserved existing refreshes/non-APT recipes, immutable saved data and restoring
the original renderer after an exception. These are synthetic semantics, not
native image or biological evidence.

For the real local comparison, reverify the same56 archived generation members,
upstream/dependency acquisitions, original helper code and original baseline
prepared package. Prepare baseline and candidate in separate owned directories.
Audit every file/mode and semantic grading/resource/deadline contract. Compare
the candidate Dockerfile to the baseline with only the declared compiler policy
delta; do not change test selection, execution or grading. An unchanged baseline
build already failed in45 and must not be rerun merely to repeat that failure.

The next native stage, if admitted, will use the ordinary frozen validator and
one candidate package with the same resource/time limits. A prerequisite build
failure means controls unattempted. A successful build is not a usable task;
original nop/oracle and300-second verifier may still fail. Do not extend those
deadlines or repair inputs in this comparison. Checkpoint exact manifests,
notice/publication policy and a maximum6.333333CPUh including stop/cleanup before
admission inside the existing32CPUh epic ceiling. No new paid capacity/model
spending. Reserve/admit only after local comparisons and source checkpoint.
