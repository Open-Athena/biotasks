# Marin conversion contract assessment

Inspection pin: `45a044387ccd95ab698b4a592056aadaff961540`.
This is source inspection, not an executed TaskSpec conversion or runtime check.

The existing task-curation repository converters are dataset-specific. The
TaskTrove `swe_task` helper requires `tests/config.json` with FAIL_TO_PASS or
PASS_TO_PASS identities and a checkout reference in the public instruction.
Native Repo2RLEnv PR-diff bundles instead carry `tests/oracle.patch`, a standalone
similarity scorer, and a shell wrapper. Feeding those bundles to the existing
SWE-smith converter would not preserve their reward contract.

The inspected model supports the necessary building blocks: `DockerBuildContext`,
separate worker/oracle/verifier resources, `ScriptGrader`, `FileReward`, and
explicit `VerifierArtifact` capture. Their presence is not an implemented
Repo2RLEnv importer. A source-specific converter must preserve these details:

| Native artifact or behavior | Required conversion behavior |
| --- | --- |
| `instruction.md` | Preserve public request; record any later correction separately. |
| `environment/Dockerfile` | Retain as an unresolved build recipe, then pin the built image before execution. Do not substitute a generic Python runtime for a repository checkout. |
| `solution/solve.sh`, `solution/patch.diff` | Oracle-only resources; preserve patch bytes and executable modes. |
| `tests/test.sh`, scorer, oracle patch, verifier instruction | Private verifier resources, delivered only for grading. |
| `/workspace` and its Git state | Capture the exact workspace needed by native `git add -A` and `git diff --cached BASE`; test deletion, ignored/untracked files, modes, and Git metadata. |
| `/logs/verifier/reward.txt` | Native floating-point reward with missing/invalid output treated as a grading failure, not silently zero. |
| Optional model judge | Explicitly disabled for this experiment; preserve native deterministic weight redistribution and score range. |

The pinned Harbor *exporter* is the reverse direction (TaskSpec to Harbor), not
an importer for arbitrary Harbor tasks. Its workspace-state path accepts only
full `/testbed` capture with a specific script-grader contract. Native PR-diff
tasks use `/workspace`; changing that path requires an explicit normalization
and native-versus-converted controls. Separate Docker build contexts also face
exporter restrictions. Atlas inventory visibility must not be presented as
successful round-trip conversion.

The first conversion case should be scikit-bio PR #2630: it has a relevant
sequence/FASTA/FASTQ request and its exported patch passes the bounded
application check. It remains an unvalidated similarity task. Use the same
bundle for reference, empty, incorrect, and valid-alternative comparisons in
both runtimes. Check learner access to hidden files, and test whether solver
edits to Git metadata can alter the captured patch or bypass grading. Do not
claim functional or biological correctness from scorer parity.

The research-recipes' separate verifier images and allowed-source collection
may require a different conversion profile. Inspect actual generated bundles
before assuming the PR-diff mapping covers them. No curriculum release or Atlas
publication has been performed.

## Pinned sources

- [TaskSpec and grader models](https://github.com/marin-community/marin/blob/45a044387ccd95ab698b4a592056aadaff961540/lib/taskcompendium/src/taskcompendium/models.py)
- [Workspace task construction](https://github.com/marin-community/marin/blob/45a044387ccd95ab698b4a592056aadaff961540/lib/taskcompendium/src/taskcompendium/convert/tasks.py)
- [TaskTrove repository input contract](https://github.com/marin-community/marin/blob/45a044387ccd95ab698b4a592056aadaff961540/experiments/post_training/task_curation/datasets/tasktrove/conversion/executable.py)
- [Deferred repository build and grader mapping](https://github.com/marin-community/marin/blob/45a044387ccd95ab698b4a592056aadaff961540/experiments/post_training/task_curation/datasets/tasktrove/repository_build.py)
- [TaskSpec-to-Harbor exporter restrictions](https://github.com/marin-community/marin/blob/45a044387ccd95ab698b4a592056aadaff961540/experiments/post_training/task_curation/tasktrove/harbor_export.py)
