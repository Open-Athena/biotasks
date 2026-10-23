# Offline historical rebuilds

## 2026-10-23 — scope

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Issue #34 is a child of #33 and uses its existing shared spending/resource budget. No new model calls or remote jobs have started. Preserve the #31 MACS PR742 failure and the pinned upstream egress guard. The first candidate prepares base-declared Python build dependencies outside the task runtime, excluding the target project itself; it does not claim to solve apt, submodules or dynamic dependency discovery. Runtime rebuild commands remain unchanged. Unsupported dependencies fail explicitly.

Source inspection found the recorded recipe also contains unquoted shell `>=` tokens. Those may be interpreted as output redirections rather than package-version constraints. Do not silently fix the recorded commands in this comparison; preserve their actual shell semantics and report the limitation. Exact commands are retained in #31 `macs-native-742-manifest.json`.

## 2026-10-23 — static preparation checks

Implemented a non-executing static pyproject build-requirement planner and wheel-identity inspection. Eight synthetic checks pass, including target-project rejection and metadata mismatch. This does not prove dependency availability, binary compatibility, compiled fixture execution, robust network isolation or task controls. The offline pip environment is a candidate configuration, not enforced isolation against arbitrary recorded commands that override it. Keep the upstream runtime network guard. Actual wheel resolution must occur on the same Python/platform as the task and retain full hashes. No downloads, model calls or remote jobs in this step.
