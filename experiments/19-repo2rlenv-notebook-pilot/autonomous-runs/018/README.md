# PyRadiomics first attempt: setup controller input-snapshot failure

Factory `bd0c81c640c1be3d7b30a958ab84264807d9d18a` processed the original pinned
PyRadiomics notebook. Preparation completed. Setup stopped when the controller's
`snapshot-inputs` helper returned an error after the setup script had completed.
The preserved traceback identifies the boundary; the underlying helper log has
not yet been retrieved or diagnosed. This is `infrastructure_failed`, not a
scientific rejection or validated task. No reference acceptance, grader or native
solver result is established.

Original small receipts were recovered and hash-checked. The host is FAILED;
setup cleanup passed and a fresh provider inventory found no owned sandboxes.
No source code or generated scientific artifact was manually repaired. Keep this
first outcome unchanged while investigating reusable factory handling separately.
