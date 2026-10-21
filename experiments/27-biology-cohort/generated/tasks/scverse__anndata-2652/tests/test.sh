#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
git checkout 9d6a4e2212350778ad737b59304dffbcb82fd7ee -- tests/test_views.py || true
git apply --verbose --reject - <<'EOF_R2E_TEST_PATCH'
diff --git a/tests/test_views.py b/tests/test_views.py
index 175a27523..72343a211 100644
--- a/tests/test_views.py
+++ b/tests/test_views.py
@@ -959,10 +959,18 @@ def test_index_3d_errors(index: tuple[int | EllipsisType, ...], expected_error:
     [
         pytest.param(sparse.csr_matrix(np.random.random((1, 10))), id="sparse"),
         pytest.param([1.2, 3.4], id="list"),
+        pytest.param([1.2, 3.0], id="list-partially-integral"),
         *(
             pytest.param(np.array([1.2, 2.3], dtype=dtype), id=f"ndarray-{dtype}")
             for dtype in [np.float32, np.float64]
         ),
+        *(
+            pytest.param(
+                np.array([1.2, 3.0], dtype=dtype),
+                id=f"ndarray-partially-integral-{dtype}",
+            )
+            for dtype in [np.float32, np.float64]
+        ),
     ],
 )
 def test_index_float_sequence_raises_error(
@@ -973,6 +981,13 @@ def test_index_float_sequence_raises_error(
         adata[index]
 
 
+@pytest.mark.parametrize("dtype", [np.float32, np.float64])
+def test_index_integral_float_sequence(dtype: type[np.floating]) -> None:
+    adata = gen_adata((10, 10))
+    subset = adata[np.array([1.0, 3.0], dtype=dtype)]
+    assert subset.obs_names.equals(adata.obs_names[[1, 3]])
+
+
 @pytest.mark.array_api
 def test_unsupported_jax_dtype() -> None:
     assert jnp is not None

EOF_R2E_TEST_PATCH
R2E_APPLY_RC=$?
if [ "$R2E_APPLY_RC" -ne 0 ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  printf '%s' '{"reward": 0.0, "resolved": false, "parse_status": "test_patch_apply_failed"}' > /logs/verifier/reward-details.json
  echo "R2E: test_patch failed to apply (rc=$R2E_APPLY_RC) — failing closed" >&2
  exit 0
fi
( . /workspace/.venv/bin/activate && cd /workspace && python -m pytest -v tests/test_views.py ) > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?
cat /logs/verifier/test_output.log
python3 "$SCRIPT_DIR/verifier.py" --log /logs/verifier/test_output.log --f2p "$SCRIPT_DIR/f2p.json" --p2p "$SCRIPT_DIR/p2p.json" --test-cmds '. /workspace/.venv/bin/activate && cd /workspace && python -m pytest -v tests/test_views.py' --exit-code "$TEST_EXIT_CODE" --out-dir /logs/verifier || { [ "$TEST_EXIT_CODE" -eq 0 ] && echo "1.0" > /logs/verifier/reward.txt || echo "0.0" > /logs/verifier/reward.txt; }
git checkout 9d6a4e2212350778ad737b59304dffbcb82fd7ee -- tests/test_views.py || true
exit 0
