# Ready-stage watch scheduling

Source candidate656c49e2 reuses the existing durable-stage contract to remove
unnecessary300-second waits between locally ready manifest transitions. Only
literal false wait hints can skip waiting; pending, missing/uncertain-handle and
unknown states retain the original interval. Once mode remains one pass; held
states stop immediately. It changes no upstream/model/task/grading/resource or
admission policy. Frozen validation, retention core and all worker assets are
byte-identical to the declared52 dependency88a02827.

All152 locked tests passed in13.79s, with lint, format, types and hooks passing.
Tests include actual generation/native/retention propagation, known stage-marker
readiness, conservative unknown handling and fake-clock watch behavior. Exact
built wheel/sdist hashes and source identities are in candidate-source-receipt.

After research driver checkpoint6dd7451f, actual old installed/new source CLI
watch functions were compared on identical synthetic state sequences with all
network/subprocess/credential access forbidden:

| Case | Old idle seconds | Candidate idle seconds | Same passes/exit |
| --- | ---: | ---: | --- |
| Four ready transitions | 1200 | 0 | yes |
| Three pending/unknown observations | 900 | 900 | yes |
| Held outcome | 0 | 0 | yes |
| Once mode | 0 | 0 | yes |

These are deterministic scheduling comparisons, not measured native speed or
model-cost improvements. Original admission flags and terminal results match.
Initial driver development output is retained separately; final proof records
the lint-clean driver hash. No native input was regenerated to test scheduling.

The candidate also read the actual active53manifest and refused adoption with
`Manifest/implementation identity changed`, without admission. The real53
controller/job remains on installed88a02827 with its original handle. No runtime
swap, grade repair, new model/native job, capacity or spending by54. Its source
and scientific outcome remain separate from this source-only fix.

Keep54/33/PR open for review and preserve the active native run unchanged. No
automatic merge or release. This establishes the scheduling contract and packaged
delivery through distribution checks; fresh native execution of this particular
timing variant is not established or required merely to exercise an interface.
