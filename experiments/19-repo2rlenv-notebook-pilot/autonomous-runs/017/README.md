# MDAnalysis rerun: response recovery works; timing contract conflicts

Factory `5478f320f0a61a66cdde53d624bff614d85bce9a` processed the original MDAnalysis
seed afresh, without generated-artifact reuse or operator intervention between
stages. Preparation, offline reference execution, fresh replays, specification
and task construction completed. Setup encountered an empty tool response at
call 60; the recorded retry obtained a tool action at call 61 and setup completed.
The original response, retry event and next response were read back with hashes.
Original failure 015 remains unchanged.

Grading stopped with `independent_comparison_unresolved`. The independent
implementation executed successfully without reference-answer access. Its RMSD
columns agreed with the reference to the proposed 1e-5 Å tolerance, but all frame
times differed by 0.5 ps. The public specification explicitly defined a header-
based time formula yielding a 0.5 ps initial time; the frozen reference began
at 1.0 ps. The grader compared against the reference and rejected the independent
output. The comparison guard stopped before further probes/review/repair rather
than automatically relaxing this disagreement.

This is rejection of a generated candidate with an unresolved public-contract /
reference mismatch, not evidence that the original scientific notebook is
broken. It does not establish which timing interpretation should define a future
task. No native Harbor solver attempt ran, and no task was published. General
follow-up: ground consequential metadata conventions in checked execution
and resolve public-contract/reference contradictions before accepting a task;
do not insert a notebook-specific offset or widen tolerances to force a pass.

The pipeline took about 45 minutes; the host including archives took about
48 minutes. Host state is SUCCEEDED, while pipeline outcome is rejected.
Original small receipts were recovered and hash-checked from bootstrap diagnostics;
the conflict and independent-control records were subsequently downloaded with
verified archive hashes through the already-active PyRadiomics host. This was
read-only recovery with no additional model or sandbox work. All four stage
ownership labels were absent in a fresh provider inventory. There were no native
trial owners, because execution stopped before that stage.
