# Pinned source observations

The official Python preset already tells the bootstrap agent to install the
project editable and recommends pretend version 0.0.0 for shallow-clone SCM
version failures. The AnnData action follows that guidance; this is not a custom
installer added by BioTasks.

The bootstrap prompt treats a successful collection count as enough to save,
and explicitly tells the agent to stop at that point. The runner commits and
caches the image even when subsequent smoke/fresh-container checks fail, storing
flags for callers. Native validation resets the working tree, applies the test
and source patches, and compares original parsed results. In these inspected
paths there is no explicit project-module import-origin/direct_url check.

These source facts are SHA-bound in source-inspection.json. Original #53 records
show both complete test runs executing the old guard from site-packages after a
clean workspace patch. A later companion dependency install replacing editable
version 0.0.0 is plausible. The quiet installer did not preserve enough evidence
to prove the exact transaction or resolved realpath/version; no such evidence is
invented here.

The next prototype should report canonical project/module paths, resolved
realpaths, file hashes and distribution/direct_url metadata, then distinguish
checkout, foreign and ambiguous bindings. A path string alone cannot reject a
legitimate editable symlink/forwarder. First test real small local package
installations and a transitive dependency replacing an insufficient editable
version. These are synthetic mechanism tests, not a rerun or repair of AnnData.
No actual prototype/native variant has been validated yet. No additional model
or native job is authorized/admitted by this source note.
