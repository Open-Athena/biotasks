# Reporting-only same-process candidate

This is a separate source/offline prototype, not installed into #53 or upstream.
The declared addition is a pytest plugin loaded explicitly with four options:
checkout root, project distribution name, requested import modules, output path.
It snapshots already-loaded modules at collection finish and session finish in
the same PID, without importing targets, changing path/install configuration or
modifying test results. It records limited loaded-function code comparisons to
current ordinary Python source; compiling source does not execute it. No score
is accepted or rejected on this report. A missing report is missing evidence.

The reason for the addition is concrete: a later independent Python process
cannot prove what the native test process imported. A file hash also cannot
identify a function already loaded before that file changed. A separate report
can expose those cases without adding an LLM stage or altering the original
AnnData verdict. It is additional instrumentation, so any future native trial
must explicitly identify it as a candidate rather than the official baseline.

Limits remain: operator module/project mapping, only explicitly named modules,
bounded .py files, top-level functions and immediate class methods. Namespace,
native/generated code, decorator substitutions, dynamically generated functions,
subprocesses/xdist, unobserved targets and absent metadata are not made valid by
this report. Current-source equality for observed functions is not complete Git,
patch, or executing-code identity. It is diagnostic evidence for nonmalicious
bootstrap mistakes, not a security or scientific acceptance boundary.

Compare real pytest baseline/candidate invocations on our own fixtures: normal
checkout, foreign release, editable-style symlink, stale loaded function after
source change, runtime-only import, namespace, never-imported target and an
original failing test. Require equal exit codes and result counts, record the
same-process origin observations and preserve the failure result. No biology
imports, network/model/native job or paid admission. Disposable fixture scratch
is task-owned under HOME and removed after reports are preserved.
