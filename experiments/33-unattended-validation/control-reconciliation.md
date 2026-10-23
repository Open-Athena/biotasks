# Recorded control reconciliation

The original cohort contains **83 distinct exported task names**, with 74 positive control pairs and 59 clean oracle commands. Later #29 controls cover nine existing tasks (Scanpy at two timeouts), adding ten pair attempts and **zero exports**. Across recorded environments, 82 tasks have at least one positive pair and 67 have at least one clean oracle command. There are 93 recorded pair slots, including incomplete original controls; this is not a count of successful executions.

The only task without a positive pair remains `scverse__scanpy-4389`. Fifteen tasks have positive tracked-test results but no clean oracle command. They remain unsuitable for a strict clean-command acceptance gate.

This is a reconciliation of recorded reports, not a fresh raw-log audit. The script verifies the six #29 input-source hashes against #28, rejects duplicate task/agent records, recomputes the original acceptance predicate, and checks later paired results against their recorded summaries. Original and reconstructed environments remain separate. Full base/head, content-hash and image-digest identity reconciliation is still pending; these counts are not release-readiness claims. The separate #31 MACS candidate is excluded.

## Positive pairs without a clean oracle command

- `matchms__matchms-304`
- `matchms__matchms-349`
- `matchms__matchms-350`
- `matchms__matchms-399`
- `matchms__matchms-405`
- `opencobra__cobrapy-1487`
- `opencobra__cobrapy-168`
- `opencobra__cobrapy-188`
- `opencobra__cobrapy-299`
- `opencobra__cobrapy-334`
- `opencobra__cobrapy-350`
- `opencobra__cobrapy-367`
- `opencobra__cobrapy-391`
- `opencobra__cobrapy-396`
- `opencobra__cobrapy-414`
