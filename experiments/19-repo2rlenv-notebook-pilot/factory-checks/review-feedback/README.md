# Actionable review-validation feedback candidate

PyMC 197 passed its 18 executed controls but timed out during final review. The original feedback repeatedly rejected structured review values encoded as strings and hint-ID coverage errors. Its last draft contained 55 assessments for 55 hints with one missing and one unexpected identity. No final scientific acceptance was recorded, and no artifact has been manually fixed.

This next-version candidate adds the missing, unexpected and duplicate hint IDs to the existing rejection message. It preserves the original coverage condition and the separate refusal to accept an exposed or unresolved hint. No ID, assessment, rationale or scientific verdict is filled in automatically. The reviewer prompt also explicitly asks for real JSON objects/arrays and verbatim opaque IDs. It asks the worker to correct a response-contract defect, never to relabel a scientific blocker to obtain acceptance.

Run `candidate.py` to print the exact two-file patch. It does not modify the canonical protocol or prompt; the 232-file panel remains frozen. Offline checks compare old and proposed acceptance across complete, missing, duplicate and unexpected identities and all three assessment decisions. A separate 55-item regression covers one mistyped opaque ID. These synthetic checks prove unchanged validation outcomes for those cases, not that a future GLM review will finish or that the PyMC task is scientifically valid.

Adoption requires a new frozen scientific version and fresh source-only execution. Retain the complete original 197 timeout and snapshot. Do not apply the change to running campaigns, manually correct the old draft, replenish its repair allowance or claim that its passing numerical controls establish release readiness.
