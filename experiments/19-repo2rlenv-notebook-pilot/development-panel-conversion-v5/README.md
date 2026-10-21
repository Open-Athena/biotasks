# Development panel: conversion profile v5

All ten pinned notebook sources converted on 2026-10-21. Each receipt records
the original bytes' SHA-256, resulting script and AST hashes, converter version,
and every normalization. Every conversion was repeated and compared for identity.
The candidate identities come from the adjacent development-panel manifest;
original v4 screening notes remain unchanged there.

This is source-only evidence: no notebook analysis, package installation for a
notebook, model call, scientific validation or paid worker was launched. These
receipts do not establish that the new notebooks run within the existing limits.
Data availability, redistribution terms and execution fit still need checking.

The general changes are:

- Translate a standalone literal `%cd` to an in-place `os.chdir` call through the
  builtin import function, avoiding a new global name. Record the original line,
  path and replacement. Reject variables, history, options, home expansion and
  other unsupported IPython semantics. A missing directory raises an error.
- Record empty code-cell tag lists and `remove-input` without skipping code.
  Unknown tags, including execution-skipping tags, remain unsupported.
- Recognize directives only at logical statement boundaries, preserving strings,
  comments and modulo expressions.

Pyteomics exercises literal `%cd`; NeuroKit exercises `remove-input`; COBRApy
deletions exercises empty tags. No source-specific branches, source edits or
manual endpoint/task decisions were introduced. The existing ordered-AST check
compares Jupytext's output to source normalized under these declared rules; it
does not prove equivalence to all IPython kernel behavior.

`check_conversion.py` checks candidate source identities against the manifest,
also checking pinned Git blob hashes when recorded, then writes each receipt and
the [summary](summary.json). Pass a manifest, a new output directory and one
original source path per candidate in manifest order. The exact local invocation
and converter hash are recorded in [execution.json](execution.json). Sources must
be reacquired from their pinned URLs if the temporary downloads are unavailable.

Validation: 65 converter tests and 138 total ordinary tests passed, along with
Ruff lint/format, ty and all pre-commit hooks. The initial sandboxed full suite
could not create loopback sockets for HTTP fixtures; the complete suite passed
with those local sockets permitted. An unrelated stale prompt-list test was
updated to derive its expected names from the actual template files. Conversion
took 0.46 seconds and peaked at 73,924 KiB RSS; the full suite took 14.52 seconds
and peaked at 75,796 KiB RSS. MDAnalysis source strings emitted Python escape
warnings during parsing; the converter did not rewrite them or execute the code.

Documentation consulted for the supported subset:
[IPython directory magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-cd)
and [Jupyter Book input hiding](https://jupyter-book.readthedocs.io/v1/interactive/hiding.html).
