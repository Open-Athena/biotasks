# Offline historical rebuilds

## 2026-10-23 — scope

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Issue #34 is a child of #33 and uses its existing shared spending/resource budget. No new model calls or remote jobs have started. Preserve the #31 MACS PR742 failure and the pinned upstream egress guard. The first candidate prepares base-declared Python build dependencies outside the task runtime, excluding the target project itself; it does not claim to solve apt, submodules or dynamic dependency discovery. Runtime rebuild commands remain unchanged. Unsupported dependencies fail explicitly.

Source inspection found the recorded recipe also contains unquoted shell `>=` tokens. Those may be interpreted as output redirections rather than package-version constraints. Do not silently fix the recorded commands in this comparison; preserve their actual shell semantics and report the limitation. Exact commands are retained in #31 `macs-native-742-manifest.json`.

## 2026-10-23 — static preparation checks

Implemented a non-executing static pyproject build-requirement planner and wheel-identity inspection. Eight synthetic checks pass, including target-project rejection and metadata mismatch. This does not prove dependency availability, binary compatibility, compiled fixture execution, robust network isolation or task controls. The offline pip environment is a candidate configuration, not enforced isolation against arbitrary recorded commands that override it. Keep the upstream runtime network guard. Actual wheel resolution must occur on the same Python/platform as the task and retain full hashes. No downloads, model calls or remote jobs in this step.

## 2026-10-23 — compiled fixture result

The first attempt rejected setuptools because vendored dist-info metadata was mistaken for multiple root distributions. Preserved the failed download log/resource record and corrected root-metadata selection with regression coverage. The second attempt completed in 4.45 seconds at 73,192 KiB peak RSS under the shared lock. With the identical `pip install -e .` command and build isolation enabled, the empty cache failed for missing setuptools; the prepared setuptools80.9.0/wheel0.45.1 cache built a C extension that imported and returned42. All temporary fixture environments and downloaded wheels were removed. This uses pip offline configuration, not OS-level network isolation; Docker guard behavior and MACS remain untested. No remote jobs or model calls.

Fetched only pyproject metadata at the exact MACS PR742 base and verified its Git blob digest. Static build requirements are setuptools>=80.0, numpy>=1.25 and Cython>=3.0, target distribution macs3. Recorded hashes and plan in `macs-base-dependency-plan.json`; runtime-platform resolution and wheels remain pending. No project hook or MACS source executed locally.

## 2026-10-23 — reconstruction launched

Checkpoint `2d6d665a` passed preflight and launched one bounded original-recipe reconstruction on an existing reserved worker; authoritative observation at22:12:04UTC reports running. See `reconstruction-submission.json` for payload hashes and resource bounds. Four CPU-hours remain reserved, not actual consumed usage. No retry, new capacity, model calls or control run. Private submission retains the exact worker binding for follow-up and cleanup. Do not resubmit this handle after interrupted observation.

## 2026-10-23 — candidate transformation and readback prepared

The original reconstruction remains running on its existing handle. Added terminal-accounting/readback helpers with duplicate archive-member rejection. Prepared the trusted base-declaration cache helper and separate task transformation. A static transformation check against the exact archived MACS task verifies nine unchanged original files, twelve final files, unchanged egress guard/test assets, refusal of mutable image tags and no overwrite. The test's synthetic digest is explicitly not an executed image, and the temporary variant was removed. Candidate Docker build and controls remain unexecuted; use the actual verified reconstruction digest before producing the real variant. See `offline-controls-protocol.md` for admission and evidence requirements.
