# Delivery diagnostic 001: ambiguous copy target

Two sequential synthetic calls used identical messages and settings, changing
only the JSON-schema response constraint. Neither matched the intended fixture:
plain JSON copied the full wrapper (schema plus object), whereas constrained JSON
returned the inner object but replaced all Markdown newlines with `</br>`.
The plain response preserved the inner text, including actual newlines after
JSON decoding. The constrained response passed the schema despite altered text.

The request said to copy the supplied object but supplied a wrapper. That is an
ambiguity in the diagnostic, not evidence of a model failure in choosing the copy
target. Iteration 002 supplies only the object to copy in both modes. Preserve
these original results; do not extract the inner plain object and call this test
passed. This observation does not establish the cause of notebook-stage failures.

Two calls: 7.07 and 2.92 seconds; no notebook analysis, sandbox or downstream stage.
Original synthetic request/response files and hashes are included.
