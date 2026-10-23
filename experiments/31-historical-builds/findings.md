# Historical build lifecycle: first findings

The original MACS archive was anonymously restored and verified against its published size/SHA256 (`restore-receipt.json`). `inspect_lifecycle.py` independently finds compiled-extension removal in seven original paired validations. No archived code, package installation or test was executed.

## An additional prerequisite: reconstructing the baseline

The saved bootstrap provides four `rebuild_cmds`, including submodule initialization and `pip install -e .`. This is enough to identify a general recorded procedure; it is not proof of successful historical replay. The saved smoke/fresh flags are false.

The separate saved `dockerfile_reconstruction` replays attempted transcript commands, including failures. Syntax-only `bash -n` checks find **three invalid RUN commands**, with trailing `</p>` text. A verbatim Docker build cannot be assumed to recreate the original image. Its build would encounter a malformed command before reaching the successful later installation. The recipe also pipes some installation commands to `tail`, so shell status can hide installer failure.

The saved dependency command contains unquoted `numpy>=1.25` and `Cython>=3.0`. In shell syntax, `>` is redirection rather than a protected version constraint. Syntax-only checks do not reject that. Quoting those strings would alter the recorded command semantics and must not be silently presented as faithful replay. No such repair has been applied.

This means a live experiment has two different questions: (1) establish an executable baseline reconstruction from an explicitly selected recorded procedure, and (2) test rebuilding after historical reset. If the first step cannot be done under the declared no-manual-repair scope, report it as a prerequisite failure, not a negative result about rebuilding.

## A rebuild must cover more than native generation

Pinned `pr_runtime_validate.py` performs reset/clean, patches, then tests; it does not replay the saved rebuild commands. Its initial `set -uxo pipefail` lacks `-e`, so reset/build/patch success must be checked explicitly by any proposed lifecycle change rather than inferred from the final marker's exit status.

The emitted environment Dockerfile also resets/cleans, and the exported verifier applies/restores patches before tests. A native-only rebuild could create an export whose independent oracle still imports stale/missing compiled code. Any proposed general hook must therefore establish correct-revision compilation in native pre/post stages AND exported nop/oracle verification. Preserving `.so` files across reset is not a valid substitute: it risks testing the wrong revision.

Before a live MACS comparison, exercise a tiny compiled fixture through all relevant reset/patch/rebuild boundaries, then freeze one original removal case and reconstruct both arms from the same base image. Record source commit, import path, compiled artifact provenance, rebuild success and test completion. A successful fixture is mechanism evidence only; full MACS positive controls remain required for a recovery claim.

## Current status

No generic lifecycle patch has been applied or live run launched. This issue remains open. Original archived evidence is retained locally under ignored `inputs-private/` while the investigation needs it; the verified public archive remains its durable backing. No `/tmp` evidence or additional model/cloud spend was created.
