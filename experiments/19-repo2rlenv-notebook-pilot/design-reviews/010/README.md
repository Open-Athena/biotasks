# Design critique 010 — truncated response

High reasoning with a 16,000-token completion limit returned an incomplete JSON review (finish_reason length). Original text and response are preserved; no schema-valid review verdict exists. It contains useful partial observations, but it was not repaired or passed into revision. Next call retains the prompt and input, increasing the completion allowance to 32,000 tokens. No construction, native validation, solver or viewer update.
