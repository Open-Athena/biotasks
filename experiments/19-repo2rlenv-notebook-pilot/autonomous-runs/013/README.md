# Autonomous attempt 013: all 23 controls pass; native stage not reached

Factory `0024293b435289b4debd5ec010224379d6a995ba` ran the original notebook
through preparation, setup, fresh replays, specification, construction and
scientific grading without operator intervention. Construction passed on its
first candidate. All 23 controls passed: five basic controls, thirteen wrong-result
probes and five valid alternatives. The review accepted the grader for packaging.
These are executable instance results, not a general software-portability claim.

Grading consumed about 83 minutes including attempted export. The probe worker
received 136 responses. An initial suite was rejected by preflight because a
wrong-output-location probe renamed a file: the controller unnecessarily required
every original output path to remain present. GLM subsequently revised its suite;
the frozen run was not patched. This failure was observed read-only in the
worker's recorded submission feedback.

Stage evidence export timed out with 153.74 seconds left in its allowance. The
pipeline therefore ended `infrastructure_failed` with zero operator interventions;
native Harbor trials and a solver attempt did not run. It is not a fully validated
autonomous task. Original small receipts were recovered with hash checks. The
host terminated and provider inventory confirmed no owned sandboxes remained.
Four dollars were reserved, not invoiced.

The next factory version separates mutation execution from grader acceptance:
successful renames/deletions are valid mutations, while no-op and crashing scripts
remain invalid. The grader still rejects unacceptable submissions. Eight regression
cases exercise this distinction and reference immutability; all 52 focused grading
tests pass, with lint passing. The general probe prompt also asks for batched
inspection, deterministic record selection rather than transcription, and reuse of
recorded facts instead of redundant reruns. Coverage and acceptance criteria are
unchanged. Campaign 014 starts from the original notebook, with no generated
artifacts reused. This is a known seed, not a held-out generalization test.
