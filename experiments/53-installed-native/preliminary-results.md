# AnnData original-pipeline result, archival/cleanup pending

The unchanged official pipeline produced zero exports for the frozen two-PR
window. Its original filter skipped backport2710 as `non_bug_pr`;2641 reached
native validation and was rejected with zero failing-to-passing tests. The
worker's successful infrastructure exit is separate from the native CLI exit1.
The automated installed controller is still completing HF/readback/cleanup; do
not call that lifecycle complete yet.

| Evidence | Original result |
| --- | --- |
| Official returned PRs | 2, one fix plus backport |
| Native PR validations | 1, PR2641 |
| Original model calls and actual OpenRouter cost | 9 / $0.313983, complete billing |
| Primary allocated CPUh | 1.5610444442431133 |
| Exports / independent exported-task controls | 0 / 0 |
| F2P / P2P identities | 0 / 1536 |
| Pre/post pytest | both2failed,1536passed,578skipped,2xfailed |
| Pre/post native exec duration | 206.13 / 206.37 seconds, both complete |

This rejection is not a600-second native-validation timeout or lack of parser
output. Both changed-file suites completed; the same new regression tests
`test_roundtrips_df_with_different_index[obs/var]` failed before and after the
source patch. The head source/test patches applied cleanly. Both tracebacks
execute the old index guard in
`/usr/local/lib/python3.12/site-packages/anndata/_core/aligned_mapping.py`, while
the patch changes `/workspace/src/anndata/_core/aligned_mapping.py`.

This strongly points to a package-source binding problem. The original agent
installed an editable checkout with pretend version0.0.0, then separately
installed Scanpy and other test dependencies. Replacing that editable package
with a released dependency is a plausible mechanism, not yet directly proven:
the quiet install output does not retain the transaction, direct_url metadata
or resolved import realpath. Do not assume every site-packages path means a
noneditable install; symlinks/import wrappers need separate checks. The original
failure trace retains the old guard after the worktree patch regardless.

Separately, both bootstrap full-suite300-second checks timed out. Collection
found9559tests, and upstream cached the flagged image. Its narrowed PR-specific
validation collected2118tests and finished in about201pytest seconds, so increasing
that validation timeout would not address this observed zero-F2P comparison.

`recorded-diagnosis.json` links the exact original archive/observation hashes,
patch application evidence, trace paths, test summaries, commands and billing.
`diagnose_recorded.py` only reads those records; no retry, task/environment/
package/parser/grader repair or extra model/native call. No accepted fresh task
or cheap-per-valid-task claim. Final lifecycle/accounting/publication/cleanup is
pending; keep53/33open. Follow up on generic source-provenance gates before
claiming a no-F2P rejection establishes an unsuitable PR.
