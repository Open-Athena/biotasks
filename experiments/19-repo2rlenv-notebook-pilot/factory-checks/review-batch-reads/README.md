# Batch independent evidence reads

PyMC 213's final grader review made 49 distinct single-read tool calls, with two unavailable items and no duplicate-call loop. Those model round trips contributed to a long review; this does not prove how much time batching will save.

The additional `read_review_evidence_batch` tool delegates each request to the unchanged single reader and returns its original result in order. It preserves the identity checks, navigation/windows, unavailable-item feedback and deadline. It adds no execution permission, scientific control, approval or new array-size cap. The grader-review prompt recommends batching independent lookups after discovering the relevant keys.

91 packet/review/proof tests pass, including a scripted transport exercising the real authoring loop. The combined review/native/execution suite passes 114 tests. Source proofs retain the original reader module after stripping only the bounded extension and exact prompt paragraph, and refuse changes to identity, reconstruction, deadlines or execution permissions. [Checks](offline-checks.json).

This candidate has not run against GLM or a notebook. It does not change the frozen 213/214 payloads. It needs a new exact source admission and a fully funded campaign before adoption; the earlier 107 admission does not admit these additional bytes.
