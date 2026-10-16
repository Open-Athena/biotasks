# Materialization 002 — tool argument failure

The worker made 41 GLM requests, then requested a 900-second shell timeout above the advertised 600-second limit. The controller correctly refused execution but propagated a ValueError that ended the entire stage. No candidate was submitted. Cleanup and the complete archived evidence download passed.

Patch 0013 returns an explicit tool error without execution for invalid timeout arguments, allowing the worker to correct them; deadline exhaustion and uncertain execution remain terminal. Inspection of the complete trace found reasoning in 9 of 41 responses (including 19,928 reasoning tokens in the first turn); 32 later responses had none. Thus the existing required-tool mechanism does support reasoning, and the initially considered synthetic probe was not launched. Absence of reasoning in individual tool turns does not establish a transport defect. No generated task code was manually changed.
