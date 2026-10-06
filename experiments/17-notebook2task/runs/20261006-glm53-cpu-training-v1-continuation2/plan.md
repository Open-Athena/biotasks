# Continue with canonical reasoning history

Preserve the original truncated response, two follow-up responses and all tool
observations. Send reasoning once under `reasoning`, rather than duplicating its
text under an alias and consuming the serialized-context ceiling. No source text
or model observation is discarded. All other limits and model settings stay the
same. The prior continuation was context-limited before it wrote any artifact.

vLLM's current primary source normalizes the deprecated reasoning_content field
to reasoning:
https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/chat_completion/protocol.py
The served vLLM fingerprint is recorded separately; this inspected source is not
proof of the precise served source revision. Actual responses use reasoning.
