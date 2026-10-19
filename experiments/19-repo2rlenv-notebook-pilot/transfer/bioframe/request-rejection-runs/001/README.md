# Recorded-request diagnostic 001

One replay of construction 002's rejected request reproduced HTTP 400. The
endpoint reports a **262,144-token context limit** and says this prompt contains
**at least 262,145 input tokens**, leaving no space for generation. The lower
bound is the provider's report, not a measured exact token count.

The source request was fetched from the original archive and verified against
its recorded SHA-256 and byte count before replay. No message, output-length
setting or scientific content was changed. This diagnostic made one completion
request plus a read-only model-metadata query; it executed no returned tools,
ran no notebook and created no Daytona sandbox. The request was definitively
rejected and its attempted slot remains counted. Provider error text was stripped
of credentials/private addresses before recording.

This confirms a context-management failure after a 1.2 MB debugging output, not a
scientific rejection or request-quota exhaustion. The original failure receipt is
unchanged. Tool-output preview restoration is a separate unresolved preference;
model generation/input/response caps have not been reintroduced.

The Iris job is terminal and the complete diagnostic archive passed download
verification. The large restored request remains in that private archive; selected
small records here are unchanged and hash-verified.
