# Python source-provenance findings

The original AnnData validation did not prove that its patched checkout was
executed. Both completed pre/post suites trace the old guard under
`site-packages/anndata`; the source patch applied under `/workspace/src/anndata`.
The original transaction/version/realpath was not retained. We preserve its zero
exports and do not retry or regrade it.

A real, fully offline synthetic pip experiment reproduced one possible mechanism:
editable `biotasks56-target==0.0.0` initially imports the checkout; installing our
companion requiring `biotasks56-target>=1.0.0` uninstalls it and imports our release
wheel. This uses actual pip resolution, not a mocked resolver. It demonstrates
possibility, not the exact AnnData transaction. The pinned upstream Python preset
itself recommends pretend version `0.0.0`; its bootstrap prompt uses successful
collection as its stopping criterion. Collection alone cannot establish origin.

`collect.py` is an experimental origin report, not a native acceptance gate. It
records distribution/direct_url metadata, requested module paths, canonical
realpaths and bounded source hashes. Eight synthetic cases pass: checkout,
outside symlink into checkout, checkout symlink out, namespace ambiguity,
missing module, import error, oversized source and an already-imported foreign
module surviving a later path change. It restores bytecode policy and does not
install or change import paths. The fixture harness changes its own toy paths.

A site-packages spelling is insufficient to reject editable imports; the actual
realpath matters. Conversely, merely placing checkout first in a later process
is not proof about the already-running pytest process. Module/project mapping
is still operator supplied, and missing distribution metadata does not make a
checkout-origin report a package-validity claim. Native extensions, namespace
identity, generated/rebuilt code and exact Git/patch identity need a declared
policy. Importing code can have side effects: any future biological collection
must execute in its target sandbox, not the trusted controller.

The next candidate should capture distribution and module identity in the same
process that runs the native tests, before/after the patch, and report an explicit
unsupported/unknown state rather than repairing imports or accepting rewards.
This would be additional deterministic instrumentation and must be recorded as
a modified candidate. No runtime integration or native/model comparison is
admitted by this initial source/offline scope. No source, installation, test,
timeout, parser or reward was changed for AnnData.

Source checkpoints: collector `542d2dd9`, real dependency-free PEP660 fixture
`908a362d`, edge harness `dde857c4`. Fixture002: Python3.13.13 / pip26.1.2, uv's
pinned offline builder; original native Python3.12.15 / pip25.0.1 differs. Runtime
1.59 seconds, peak45,676KiB. Initial fixture001 could not resolve an uncached
build backend offline and is retained separately as a setup failure. Initial
edge001 hit a synthetic finder-directory cache; edge002 invalidates finder
caches for newly written fixtures without clearing the imported module cache.
The collector was unchanged. Neither failed harness run is native evidence.

All inputs are our own synthetic packages, not biological observations. No
network, new native jobs, model/solver calls or extra spend. Small source,
reports, commands, failed/successful logs and hashes are Git-versioned; owned
fixture environments and scratch are removed, retained toy sources/wheels stay
under HOME. No owned `/tmp` data. Keep #56 and #33 open for review; no promotion,
merge, dataset release or accepted fresh task is claimed.
