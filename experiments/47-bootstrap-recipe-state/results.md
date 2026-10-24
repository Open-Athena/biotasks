# Source assessment

The frozen native source and all56 extracted generation members were reverified
against their original acquisition/readback hashes, byte sizes and file modes.
`assess.py` performs only bounded local reads; it executes no saved command and
uses no model, subprocess, remote job or credential. `source-assessment.json`
preserves the exact selected evidence and native function ranges.

The first live `apt-get install libexpat1` could not locate its package. A later
recorded action successfully executed `apt-get update -q && apt-get install -y
libexpat1-dev ...`. The saved rebuild list retains the install but omits the
update. This omission is already present in the bootstrap agent's saved result;
it was not introduced by our local handoff. The original inline emitter adds a
git/CA prelude that deletes package indexes, then appends saved commands verbatim.
Independent clean reconstruction consequently fails at the install, as the
unchanged baseline archive records. Merely preserving the prelude's indexes is
not a general guarantee: when git/CA already exist, that prelude may skip update.

There are two different verification boundaries. The native bootstrap smoke
check executes saved test commands inside the live environment. The fresh-image
check starts a new container **from the committed live image**. Neither rebuilds
the clean inline Dockerfile from saved commands. Both are soft flags in the
native runner, and the recipe reader does not enforce them. The observed fresh
flag was false because of a300-second test deadline; it is not evidence that
that fresh-image check encountered the later APT reconstruction error.

The ten transcript rows contain one format-invalid response;11 provider calls
are fully billed. The successful SAVE_SETUP returns before appending its own
transcript turn, explaining the count difference without inventing missing
calls. The existing parser remains unchanged.

The narrow candidate worth testing is an explicit generic package-index policy
at recipe emission, preserving saved commands and limiting any normalization to
unambiguous APT install forms. A separate build-acceptance gate would detect
incomplete recipes instead of silently calling them portable. These are proposed
policies, not applied repairs or native successes. A general shell parser,
dependency inference, model repair, timeout change and replacement grader are
outside this comparison.

Before execution, define supported syntax, meaningful negative fixtures,
candidate provenance and exact raw/candidate grading/resource equality. Keep
the failed official baseline untouched. A build recovery would still leave the
original300-second verifier versus over430-second native-suite duration, and
the existing remote-model-load failure, to measure separately. No new remote
admission or model call has occurred in child47.
