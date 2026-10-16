# Materialization 002 — tool argument failure

The worker made 41 GLM requests, then requested a 900-second shell timeout above the advertised 600-second limit. The controller correctly refused execution but propagated a ValueError that ended the entire stage. No candidate was submitted. Cleanup and the complete archived evidence download passed.

Patch 0013 returns an explicit tool error without execution for invalid timeout arguments, allowing the worker to correct them; deadline exhaustion and uncertain execution remain terminal. All 41 recorded responses contain zero reasoning characters/tokens despite requesting medium effort. That is an observation, not proof that the service disabled reasoning. A matched synthetic required-versus-auto tool-choice diagnostic is being prepared before another scientific campaign. No generated task code was manually changed.
