# Autonomous attempt 008: active command log removed by worker cleanup

Factory `c3ac30991194faadede2c423832a5ec11fbc3668` started from the original
motifs-to-peaks notebook without prior generated task artifacts. Preparation
completed. During setup, GLM issued a workspace cleanup command that included
`rm -f /work/logs/*.log`. The controller had already opened that command's output
log there; unlinking it made the subsequent download fail. The command itself
returned, but its output was lost. This is a controller infrastructure failure,
not a scientific rejection or a validated task.

The failed operation was recovered unchanged from the verified archive using a
short, read-only reserved CPU recovery job. Both the campaign and recovery host
terminated. The stage cleanup passed and an independent provider inventory found
zero owned Daytona sandboxes. The one-dollar reservation is not billed usage.

The general fix spools active output into an anonymous file and materializes the
named log after the child processes end. Workspace cleanup can no longer unlink
the active log. Disk copying is bounded in memory; scientific files and worker
instructions are unchanged. Seventeen focused logging/setup tests pass, including
real subprocesses that delete the logs directory before exiting or timing out.
The next campaign starts from the notebook again; live effectiveness is unproven.
