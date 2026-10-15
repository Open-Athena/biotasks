# Delivery diagnostic 002: constrained response changed newlines

With the copy target made unambiguous, ordinary JSON preserved the exact fixture,
including Markdown newlines. The constrained JSON-schema response replaced those
newlines with literal `/n` text. Both passed schema validation; only ordinary JSON
passed exact-content comparison. The two requests differ only by response_format.

| Mode | Schema valid | Exact fixture | Seconds |
| --- | --- | --- | --- |
| Ordinary JSON text | yes | yes | 3.36 |
| Constrained JSON schema | yes | no | 1.48 |

Inspect [results](result.json), [ordinary response](plain_json/response.json) and
[constrained response](json_schema/response.json). All original files match their
archive hashes. This is evidence of a content-fidelity problem associated with
the constrained-output path in this test. It does not identify a serving-code
root cause or establish that every notebook-stage failure has the same cause.
There was one sample per mode, without a fixed sampling seed.

The next diagnostic keeps the full specification prompt and evidence unchanged,
removing only the server response constraint. It still parses JSON and invokes
the same local artifact/schema validator; malformed outputs stop without repair.
The default configuration remains structured JSON pending that comparison.
No scientific computation, tools, sandbox, construction or solver ran here.
