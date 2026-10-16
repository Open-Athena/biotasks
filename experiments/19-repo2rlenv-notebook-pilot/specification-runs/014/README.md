# Scientific task proposal 014 — revision required

The GLM worker returned a fixed-group marker-analysis proposal in 41 requests
(631.8 seconds for the recorded stage), with read-only package inspection and no
sandbox or scientific execution. The host succeeded. Original outputs are retained
unchanged; this is not an accepted solver contract.

The proposal uses raw expression plus sample/barcode/group metadata and excludes
clustering and UMAP. It expresses statistical methodology rather than an exhaustive
API recipe. However, operator review found contradictory ranking directions,
unmeasured numeric tolerances and an automatic safety factor, an arbitrary top-50
boundary, an auxiliary normalization-summary target absent from saved outputs,
and an incorrect claim that disabling continuity correction makes asymptotic
Mann-Whitney equivalent to an uncorrected-tie reference. The public p-value formula
also invites cancellation if implemented literally. Some purported wrong methods
need not change rank-based statistics under monotone transformations.

These are reasons for worker revision, not manual edits to its task. The next
pass receives this proposal and specific critique, with generic prompt corrections
against invented tolerance values, unsupported equivalence, extra summary targets
and incidental identity conventions. It reuses recorded source facts in one
structured response, without repeating package inspection. The official SciPy
reference states that the asymptotic method corrects for ties separately from
continuity correction: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html

All 104 recovered files were checked against archived hashes. Only 37 of the 41
raw response files fit the bounded diagnostic recovery; the full archive retains
all requests/responses. The response summary describes recovered files only.
No grader, materialization, solver, release or viewer change ran in this campaign.
