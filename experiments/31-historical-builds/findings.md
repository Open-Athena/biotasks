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

## Compiled lifecycle mechanism check

`check_compiled_lifecycle.py` executes the pinned upstream native-stage and exported-verifier builders against a synthetic C shared library. It verifies source hashes before AST-loading only those functions. Local execution remaps the absolute sandbox/log paths into an owned temporary directory; it does not install/import the upstream package or run Docker/Harbor.

Twelve cases pass explicit assertions:

- Original native and exported reset/clean paths remove the bootstrap library; neither nop nor oracle imports it successfully.
- A research adapter runs the same deterministic compiler command after source patches and before tests. Both paths then import value 1 from the base source and value 2 from the patched source; nop fails and oracle passes. Binary hashes distinguish the two builds.
- An explicit negative control restores the fixed-ref bootstrap binary after reset. The exported nop then passes incorrectly despite unfixed source. Retaining compiled files is therefore not a valid substitute for rebuilding in this fixture.
- A multiline rebuild starting with `false` stops both paths before tests, even when followed by a successful command. The adapter uses a separate `bash -euo pipefail -c` process and explicitly checks its status: wrapping a `set -e` subshell in an `||` list would suppress errexit.

The final run took under one second and peaked below 25 MiB RSS; all temporary fixture files were removed. It uses no biological data, model calls or remote capacity. Exact results and resource accounting are in `compiled-lifecycle-results.json` and `compiled-lifecycle-resources.txt`.

These are mechanism checks, not an integrated candidate or MACS recovery. The export check uses upstream's binary-reward fallback, not the graded parser. The adapter does not yet cover reset/patch failure guards, configuration plumbing, emitted metadata, dependency drift or full native validation outcomes. Those remain required before a live comparison.

## Current status

No generic lifecycle patch has been applied to a repository pipeline and no live repository run has been launched. This issue remains open. Original archived evidence is retained locally under ignored `inputs-private/` while the investigation needs it; the verified public archive remains its durable backing. No `/tmp` evidence or additional model/cloud spend was created.
