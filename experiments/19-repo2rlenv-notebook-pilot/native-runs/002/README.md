# Native 002 — controls passed, solver request rejected locally

Harbor oracle scored 1 and no-op scored 0. The blind solver request was rejected by the local gateway before reaching GLM: the gateway still required max_tokens even with output_tokens=None. No provider model request was recorded, and no solver reward exists. This is an integration failure, not a solver failure. Complete archive downloads are verified; all three trial supervisors and independent provider inventory confirm cleanup. The exact package is retained with its bundle hash.
