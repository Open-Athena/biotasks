# Diagnosis of the original input-snapshot failure

The original failure remains unchanged. On 21 October, a bounded read through the already-running campaign 023 host recovered and hash-verified the original helper log and candidate staging files. No additional host or model call was used.

The helper raised `ValueError("Invalid staged input path")`. Four recorded files were under the allowed `/work/cache` root; the fifth was `/work/examples/exampleSettings/Params.yaml`, outside the controller's allowed `/inputs` and `/work/cache` staging roots. The worker placed it there to satisfy the source notebook's relative path, but the factory required the inventoried copy inside an approved root.

This establishes a generated setup-inventory defect that the old factory surfaced as an infrastructure failure. It does not establish a broken scientific notebook or a successful reference run. The newer generic inventory validator and typed staging-error feedback (already present before recovery, factories `d2fe1874` and `f8e3c877`) address this error class. A future GLM worker must repair staging within its existing allowance; no original candidate was edited and no successful rerun is claimed.

The recovered candidate's data-license statements are model-authored assertions, not an independent redistribution review. No biological data is included here. Original diagnostic bytes and hashes are preserved in `recovery.json`.
