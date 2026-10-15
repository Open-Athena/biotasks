# Specification 011: narrower assignment, public-draft defects remain

The worker returned `draft_ready` under the reference-defined target with open
solver tool choice. It correctly leaves acceptance rules for later executable
validation, but operator review does not accept this public draft. Original
model content is preserved unchanged.

- [Generated review](review.md)
- [Generated public brief](task-brief.md)
- [Generated validation handoff](validation-handoff.md)
- [Inspection sequence](inspection-summary.json)
- [Original-file identities](artifact-manifest.json)

Factory checkpoint: `4edfd5de467d7202bd07d600836099b5fd22b7cf`. The actual initial
API request matches the canonical prompt and input 011. One GLM-5.3 medium
session used 79 requests and 470.59 seconds of worker time. The remote job and
local clients are terminal. No scientific execution, construction, solver or
viewer update occurred.

## Findings

1. **Measured results leak into the public recipe.** The brief includes the
   observed number of retained cells, cluster counts and label ranges. These are
   generated answers, not source-defined methodological parameters. A reference
   recipe should define operations and symbolic output cardinality (for example,
   one row per retained cell), without copying observed result sizes.
2. **Unnecessary implementation paraphrases introduce errors.** The duplicate
   barcode example describes changing existing suffixes rather than appending
   suffixes to the complete original identifier. The source's named index-unique
   operation can define the convention without an invented example. The response
   also expands library internals more than the narrower assignment requires.
3. **The handoff still contains speculative checks.** Its proposed comparison of
   cluster cell counts with DE rows per group confuses two populations: a ranked
   gene table has gene rows, not cell rows. It also asserts within-build
   determinism before acknowledging that repeatability has not been measured.
   These claims are not needed to identify unresolved validation questions.

Keep reference operation names, versions and explicit source arguments as the
normative recipe, with purpose-level prose instead of unnecessary internal
algorithm expansions. Keep measured output facts in the private review. Request
only unresolved comparison questions in the handoff. These are general changes,
without notebook-specific methods or manually repaired task text.

## Evidence retention

Seven copied original small files match the remote manifest. The complete event
trace was recovered and hash-verified; 70 raw responses were locally recovered
out of 79 requests, not a complete token-usage report. All original records and
package archives remain in durable storage. The bounded recovery did not include
the standalone handoff file; `validation-handoff.md` is a lossless extraction of
the original `specification.json` field with one terminal newline, not a manually
edited response or a claim of byte identity to the unrecovered standalone file.
