# Rooted pytest targets across working directories

The source-bound opt-in adapter fixes newly appended Python test arguments by
anchoring them under the native checkout and applying POSIX shell quoting.
It leaves the working directory, test content, install/import paths, native
parser/reward and resource/deadline contracts unchanged. There is no repository
or PR branch. Recognized existing targets, quoted targets and node IDs are
preserved; non-pytest commands retain the original targeter's behavior.

At candidate c002dcfd / source review 5097982b, eight paired real pytest layouts
(16 processes) pass. Root and existing-target cases preserve actual test cases,
exit codes and original parsed statuses. Nested directories, multiple files,
new paths containing spaces and a quoted working directory recover from the
original file-not-found exit 4 to real passing tests. Existing quoted targets
and node IDs remain one requested test. Independent fixture JUnit records and
original parser results are both preserved; JUnit is not substituted for the
native parser or reward. Two filename-with-space cases execute successfully but yield zero test identities
under the unchanged original parser. They are unsupported for scientific
acceptance; JUnit is not used to rescue them or change the parser.

Unsafe absolute/traversing/NUL paths and an unexpected
upstream callback result reject explicitly. No model/native job or deployment.

Latest official source at 0.9.4 / 4b29471c changes runner aliases to recognize
`py.test`; the entire helper is therefore not identical. Executing that actual
current helper on the original recorded Biopython command still appends the
same wrong relative path. This is a limited helper/source observation, not a
native Biopython validation: #57 skipped its PR before validation.

The adapter remains a declared modified candidate. Recognized Python targets
only; inherited option-value ambiguity, unsupported runner forms and upstream
file extraction are not made universally correct. All tests use our own
synthetic files, not biological imports or task repair. Native integration
requires exact policy/runtime/manifest binding and separate budget admission,
with #58's official filter option recorded as another distinct setting. The
original #57 lifecycle must finish first. No accepted fresh task, release or
whole-pipeline readiness is inferred from these fixtures.

Complete commands, stdout/stderr, JUnit identities, native parser tables and
negative cases are in policy-proof.json. Owned fixture scratch is removed; no
owned /tmp data. Keep #59/#58/#33 open for review, no merge or release.
