# Specification 009: interrupted source-inspection session

Factory checkpoint: `642586735a183bc5a6ef61e0b6d23354150440fa`.

The worker used the revised generic prompt and unchanged run-007 input/tool contract. It received 50 model responses, comprising 25 successful file reads, 20 searches, three directory listings and two invalid-argument tool responses. The next request failed with `APIConnectionError`; its ledger slot remains uncertain rather than being counted as a completed response. Elapsed worker time: 500.94 seconds. No artifact was submitted, no response was manually repaired and no automatic retry occurred. The remote host and local clients are terminal.

This is an incomplete infrastructure outcome, not a scientific disposition. [Result](result.json), [transport failure](transport-failure.json) and [derived inspection sequence](inspection-summary.json) preserve the observed status. All original records remain in the verified remote archive; 47 of 50 raw responses were recovered locally, so their usage summary is not a campaign total. Five small original files are hash-verified in [the manifest](artifact-manifest.json).

The documented service route still reports running. Specification 010 is an operator-launched fresh session with the same prompt, evidence, tools and bounds, within the user's iteration authorization. It does not resume or silently retry the uncertain request. No sandbox, scientific execution, construction, solver or viewer update occurred.
