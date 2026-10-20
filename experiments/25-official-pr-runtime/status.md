# Experiment complete: zero exports

The official pipeline ran with unchanged upstream source and the approved Docker
resource wrapper. Scikit-fingerprints and PsychoPy exhausted their 20-turn native
bootstrap limits. Nipype saved an environment, selected six PRs, filtered four for
missing test patches, and rejected two after parsing zero pre/post tests.

No tasks were exported, so base/reference grading had no inputs. There were 49
native agent iterations, including 17 invalid actions, and no external model
repair calls. Native cost estimates were zero and are not a measurement of billed
spend. Final recorded compute use was 1.506342 allocated CPU-hours.

All five jobs are terminal. Archive readback and owned-container/image cleanup
passed. See [results](results.md), [structured outcomes](evidence/final-outcomes.json)
and [verification](verification.json). This is a negative result for the tested
configuration, not a general rejection of PR-derived task generation.
