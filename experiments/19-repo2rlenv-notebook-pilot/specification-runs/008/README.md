# Specification 008: infrastructure failure before model invocation

Factory checkpoint: `c11b4f76e665c5a39457d2492b15746c26214db3`.

The remote host failed during model-endpoint discovery after installing the runtime. The approved route had no available endpoint in that cluster. The specification worker was never invoked: zero model requests and no generated specification. This is not a prompt-quality result. The original bootstrap status is preserved; full startup diagnostics were archived by the host. No reference execution, sandbox, construction, solver or viewer change occurred.

Specification 009 retries the same prompt, input and tool configuration through another documented route to the same GLM-5.3 service on reserved CPU capacity. No scientific evidence or model settings change.
