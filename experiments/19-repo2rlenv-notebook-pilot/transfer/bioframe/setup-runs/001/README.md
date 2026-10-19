# Bioframe reference setup 001

The tool-enabled GLM-5.3 worker completed the existing setup stage in 312.39
seconds using 40 model requests. The one controller-owned reference test ran
successfully offline in 4.80 seconds, with 0.54 GiB maximum child RSS, and
produced a 2,484,403-byte CSV with 40,557 rows and nine columns. An independent
archive download verified its SHA-256 and structural profile. This establishes
execution and file integrity; independent scientific equivalence and a validated
task/solver result have not been established.

The worker selected bioframe 0.8.0 and pandas 2.3.3 after detecting pandas 3's
changed chained-assignment behavior. The recorded source diff changes only
three input reads to their staged local paths. Original algorithms, plotting
calls and appended exports are preserved. All three input files were verified
unchanged after execution. The source has experimental ChIP-seq peaks and a
predicted JASPAR motif-site annotation track, rather than synthetic replacements.

The provider independently reported zero owned sandboxes after cleanup. The
setup host and the two read-only archive recovery/audit jobs are terminal.
Dependency lockfile and prompt recovery required a general diagnostic-exporter
fix: prioritize replay prerequisites and admit larger reference lockfiles while
retaining the existing total transfer bound. No extra model or scientific run
was launched for recovery.

## Known factory limitations

The prompt requires scientific computation to use `test_reference`, but the
worker also ran analyses through the setup shell. Selected original operation
records are in `shell-exploration/`. Therefore `controller_reference_tests: 1`
is not a count of all scientific runs. The session's time/resource limits still
applied. This is a workflow-compliance limitation, not independent validation;
matching an exploratory run from the same worker is not independent scientific
reproduction.

The preparation response's description of whole-peak removal is imprecise:
`bioframe.subtract` can trim/split intervals. Preserve the actual source semantics
in later task specification and comparison rules. HFF attribution is present in
the source notebook narrative; the earlier operator concern about it was
corrected separately from the unchanged worker output.

`artifact-manifest.json` preserves original hashes for selected evidence.
`output-audit.json` describes an independently downloaded output without adding
scientific computation. Large inputs/results and full raw request/tool traces
remain in the configured archive, not Git. The small reference evidence follows
the existing loader layout so replay/specification can use it directly.
