# Replay wrapper acceptance policy

The #40 source assessment at `cc85fee0` identified an additional fidelity difference in this outer wrapper. Pinned upstream Repo2RLEnv runs smoke/fresh checks, records their booleans, and commits/caches the image even when those checks fail. The PR-runtime consumer does not use these booleans as hard rejection gates.

The #39 `Initializer` reuses the original check implementations but adds hard stops when smoke or fresh verification is false. Its two-PATH-export diagnostic probe also reflects the OHIF test prelude. These are outer acceptance/instrumentation choices in addition to resource/ownership adaptations; they must not be described as unmodified upstream acceptance semantics or universal language support.

Both native checks passed in the actual #39 OHIF run, and its original independent controls passed. This finding does not change those observations or their source/image identities. It limits transfer: Scanpy's retained checks are false and its verifier activates a venv, so the current wrapper cannot transfer unchanged. The original raw evidence and frozen #39 executable inputs remain unchanged; no gate was relaxed and no new runtime was performed.
