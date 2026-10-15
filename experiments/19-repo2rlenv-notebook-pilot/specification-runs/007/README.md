# Specification 007: source inspection works; scientific draft not accepted

The read-only specification session completed and submitted a readable,
schema-valid `draft_ready` response. The operator review below does **not** accept
that scientific disposition. No construction, solver, scientific rerun or viewer
update occurred. Generated files are preserved unchanged.

- [Generated review](review.md)
- [Generated public task brief](task-brief.md)
- [Generated private validation plan](validation-plan.md)
- [Inspection and submission sequence](inspection-summary.json)
- [Original-file identities](artifact-manifest.json)

The factory checkpoint is `9b16568c995dca363e5883375c8adcb346a8c343`.
The session used GLM-5.3 medium, the unchanged setup-001 reference and
preparation-010 exports, and the [reviewed input/tool contract](../../specification-inputs/007/README.md).
Elapsed stage time was 1,539.97 seconds (25 minutes 40 seconds): 79 model calls,
comprising 32 source searches, 46 file reads and one successful submission. One
file read used an inverted line range; the tool rejected it and the worker
corrected the range on its next turn. There was no failed artifact submission,
transport retry or replacement session. Both the remote job and local clients
are terminal.

## What improved

The worker inspected hash-verified Scanpy 1.12.4 and AnnData 0.13.4 wheels and
the igraph 1.0.0 source archive. It established several previously missing
implementation details, including the per-invocation clustering iteration
default, identifier-disambiguation code and differential-expression formulas.
It returned substantive English Markdown through the native artifact tool, with
normal line breaks and no placeholder fields. This demonstrates successful
delivery in this session, not a diagnosis of the earlier serving failures.

The 78 inspection actions also show that this was a substantial source-reading
session, not a fixed small number of calls. The tools expose general package
files; neither the factory nor the prompt supplies a seed-specific symbol list.

## Why this draft should not advance

1. **The prose combines mutually exclusive feature-selection modes.** Public
   step 9 applies mean/dispersion cutoffs within each sample despite the source
   call explicitly requesting `n_top_genes=2000`. In this release those cutoffs
   are ignored when the top-N option is supplied. The relevant evidence is
   `scanpy/preprocessing/_highly_variable_genes.py:705–718`, which the worker
   actually read, plus the dispatch in `_Cutoffs.validate` and `_subset_genes`.
   The draft therefore specifies a different per-sample selection rule, which
   can change the merged feature set and downstream analysis. Access to source
   did not ensure correct interpretation of argument precedence.
2. **The proposed valid relabeling changes biological meaning.** The public
   brief treats community numbers as arbitrary across solutions but requires
   a fixed number-to-lineage dictionary. Validation section 4.5 then says to
   permute community labels and reapply that dictionary as a valid control.
   For example, exchanging community labels 0 and 1 while keeping memberships
   fixed would exchange their named annotations under a fixed dictionary.
   That changes the annotated result; it is not merely a representation change.
   It also conflicts with the plan's prohibition on rematching lineage names.
   Numerical calibration cannot decide which interpretation the task means.

These are sufficient reasons to withhold acceptance; this is not an exhaustive
scientific validation of every generated instruction. Independent review also
confirmed the identifier-disambiguation implementation using the same tools
against the pinned AnnData wheel, without installing or executing package code.
Those operator checks were not supplied to the worker.

## General implications for the next revision

Keep the read-only mechanism. The next prompt revision should require checking
the active implementation branch and argument precedence when translating code
into prose, and testing each permitted representation change against all
dependent outputs and named scientific meanings. A contradiction in those rules
is a drafting blocker, not a future tolerance-calibration item. These are general
checks, not instructions about this notebook's algorithms or desired answers.
No generated task text has been manually repaired, and no new model session has
been launched from this review.

## Evidence retention

All eight copied original files match their remote export hashes. The complete
request/response history, tool trace and three verified distribution archives
remain in the original durable archive. The bounded diagnostic transfer recovered
the complete tool-event trace and 15 of the 79 raw responses; `response-summary.json`
explicitly describes that subset and is not a campaign-wide token total.
`inspection-summary.json` is a derived navigation view of the verified trace:
source text and search matches are omitted, while queries, ranges, identities,
result counts, errors and the final submission are retained. The original trace
was not edited.
