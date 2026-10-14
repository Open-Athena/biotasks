# Schema-enforcement probe 001

**Strict tool arguments failed this probe; JSON-schema response format passed.**
Two independent GLM-5.3 requests used the actual ReferencePlan JSON schema and
the same tiny synthetic fixture. The prompt deliberately requested omission of
required `changes` and an extra `unexpected_field` in a nested branch.

| Request mode | Observation | Schema validation | Model-call time |
| --- | --- | --- | --- |
| Tool with `strict: true`, `tool_choice: required` | Omitted `changes`; included the forbidden nested field | Failed both constraints | 2.48 seconds |
| `response_format: json_schema`, `strict: true` | Included `changes`; excluded the forbidden nested field | Passed | 2.13 seconds |

[Results](result.json), [exact schema](schema.json),
[tool request](strict_tool/request.json), [tool response](strict_tool/response.json),
[JSON-schema request](json_schema/request.json),
[JSON-schema response](json_schema/response.json), [receipt](run-receipt.json).

The response-format result supports using that interface for preparation. A
single passing example does not prove universal enforcement, scientific fidelity
or correctness of source edits. Local Pydantic and semantic checks remain
necessary. This does not establish which internal serving component ignored the
strict tool schema, nor whether run 003's omissions arose in generation or in
its tool parser. The deployed serving revision was not independently verified.

The probe requested medium reasoning, no client output-token/byte caps, a
600-second request timeout and no automatic retries. Across both requests it
used 1,393 prompt and 1,103 completion tokens, including 754 reported reasoning
tokens. No notebook generation, biological installation, generated-code
execution or sandbox occurred. The reserved CPU host is terminal. All eight
original probe evidence files were recovered and hash-verified.

The implementation now uses JSON-schema response format for preparation,
submits the complete returned object to the existing upstream validator, and
requests a complete replacement on the one allowed repair. It does not merge
patches or infer omitted fields. Tool-based workers in other stages are unchanged.
