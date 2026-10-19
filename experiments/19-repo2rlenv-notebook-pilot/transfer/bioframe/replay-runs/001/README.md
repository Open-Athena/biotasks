# Bioframe deterministic replay 001

Both fresh-process repeats produced byte-identical outputs to the original
controlled reference test. No LLM calls were made. This used the same rebuilt
locked environment and caches, rather than independently implemented methods.
The base-image tag was reused, not pinned to an immutable digest.

The replay worker completed in 47.01 seconds, reported successful cleanup, and
retained all file identities in the configured archive. Original comparison and
trial receipts are preserved here. Repeatability is observed for these finite
runs; scientific equivalence, grading tolerances and solver success remain
unestablished.
