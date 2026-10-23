🤖 Reopened for the requested all-ten failure diagnosis. The original campaign is finished, but the issue will remain open until the user is satisfied with the findings and next steps. Earlier closure/completion records describe that campaign and remain preserved.

[Diagnosis and proposed controlled comparisons](https://github.com/Open-Athena/biotasks/blob/af4b8656/experiments/28-catalogued-fields/history-wide/failure-diagnosis.md) distinguishes the following:

- OpenMS stopped at a hard-coded 60-second checkout timeout; MMseqs2 stopped at the configured 30-minute bootstrap deadline. Longer allowances are plausible tests, not demonstrated fixes. Inner command and turn limits remain separate.
- Scanpy needs a complete nop/oracle comparison using its existing export and a longer verifier allowance. Matchms/OHIF have 14 individual controls that never started; these need more queue allocation before changing per-command timeouts.
- SAMtools has unsupported test conventions; LAMMPS has action-to-shell protocol contamination as well as build timeouts; MACS loses compiled extensions during historical reset; MNE has broad test selection and ANSI-sensitive parsing alongside timeouts. Increasing time alone does not address these mechanisms.
- MACS, Matchms, Cobrapy and OHIF share 33 argument-limit exceptions consistent with upstream embedding scripts/patches in one shell argument. A generic stdin/file transport change deserves a separate controlled test.
- Cobrapy's ten positive-but-unclean commands retain exactly their base controls' untracked failures. Matchms has five analogous cases. These are not new oracle regressions. Backlog is also distinct from failed validation.

Recommended order: finish unstarted controls; test Scanpy's verifier allowance and OpenMS/MMseqs2's limits separately; then test generic transport, environment-lifecycle and runner support changes. Preserve original inputs/results, predeclare cases and change one factor at a time where possible. No blanket rerun, extra repair-model calls, native changes or additional spending occurred in this review. Proposed settings and code changes remain untested.
