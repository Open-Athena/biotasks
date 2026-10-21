# Fresh autonomous payload isolation check

Factory `92a1e6f5562be9de7652e3ac35e3d58b05b452ca` built a fresh PyHMMER payload
from the original seed. Its code archive is **260,067 bytes**, compared with
**16,090,804 bytes** under the complete-checkout policy for the same seed. The
upstream runtime archive remains unchanged and is not included in that ratio.

The preserved executed checker verifies every submitted file hash, extracts the
archive, checks the sole notebook's original hash, verifies all 13 upstream
patches, and loads eight runtime modules with an explicit assertion that their
files come from the extracted payload. It also runs deterministic notebook
conversion in the project environment without executing the notebook's analysis.
The result is in result.json; the exact executed source is executed-check.py.

All checks passed. No scientific computation, model call, dependency rebuild or
sandbox run occurred in this local check. It reuses the existing project and
upstream environments and does not establish fresh remote installation or
end-to-end scientific validity. The expanded local payload/reference/setup/
evidence/orchestration suite passed 72 tests; its real-Git archive case checks
literal filenames, exact selected bytes, runtime assets and exclusion of other
seeds and past outputs. Continuation workflows retain their complete archive.

The local check completed in 2.62 seconds, with reported peak RSS 122,380 KiB.
Submission of the compact payload subsequently peaked at 315,588 KiB, versus
441,924 KiB for the earlier full-source submission. These observations support
the payload-growth improvement; they do not establish the cause of the stalled
Iris handoff or prove that the compact payload resolves it.
