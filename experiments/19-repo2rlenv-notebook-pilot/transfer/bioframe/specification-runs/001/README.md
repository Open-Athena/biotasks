# Bioframe task specification 001

The existing GLM-5.3 specification worker returned a draft after 20 requests
and 548.25 seconds, using the unchanged canonical prompt and the existing
read-only package-source tools. It proposes one scientific endpoint: assign
strongest overlapping CTCF motifs, then subtract expanded blacklist intervals.
The question states two analysis steps and an output schema, without requiring
specific function calls. Software choice remains open.

The proposal correctly distinguishes trimming/splitting from dropping entire
peaks, preserves assignment before subtraction, and expresses the reference's
motif tie rule in terms of input-file order. It renames motif output columns
for clarity and permits arbitrary output-row order.

This is a draft: duplicate input keys, missing motif scores and tie incidence
still need executable checks. Numeric precision and negative-control
classification are proposals, not validated grading rules. No task construction,
grader, solver attempt or publication has occurred for this notebook.

Original output is unchanged. The operator selected only evidence/policy paths
and the existing package-inspection mode; no replacement scientific design was
provided. Full original requests, responses and package archives remain in the
configured archive; the manifest and inspection summary identify the source
of the selected small records here.
