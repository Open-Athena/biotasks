#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
git checkout 71286a24bddff66c82cb25a7ca13441aa13c2f2c -- skbio/stats/composition/tests/test_ancombc.py || true
git apply --verbose --reject - <<'EOF_R2E_TEST_PATCH'
diff --git a/skbio/stats/composition/tests/test_ancombc.py b/skbio/stats/composition/tests/test_ancombc.py
index 83450d87b..f68465bc5 100644
--- a/skbio/stats/composition/tests/test_ancombc.py
+++ b/skbio/stats/composition/tests/test_ancombc.py
@@ -1183,6 +1183,28 @@ def test_estimate_bias_em(self):
                         [-0.1981 , -0.19314,  0.00187]])
         npt.assert_array_equal(obs.round(5), exp)
 
+    def test_estimate_bias_em_underflow(self):
+        # Regression test for #2631. Tiny coefficient variances can make all
+        # three Gaussian densities underflow to zero for a feature. ANCOMBC
+        # treats the resulting undefined responsibilities as zero.
+        table = pd.DataFrame(
+            [[154, 188, 68], [143, 63, 177], [30, 154, 96], [131, 167, 150]],
+            index=list("abcd"),
+            columns=["f0", "f1", "f2"],
+        )
+        metadata = pd.DataFrame(
+            {"g": pd.Categorical(["a", "a", "b", "b"])},
+            index=list("abcd"),
+        )
+
+        result = ancombc2(table, metadata, "g", p_adjust=None).result
+        observed = result.xs("g[T.b]", level="Covariate")
+
+        expected_lfc = [-1.08292235, 0.16646377, -0.13155807]
+        expected_pvalue = [0.25770796, 0.85244671, 0.87755871]
+        npt.assert_allclose(observed["Log(FC)"], expected_lfc, atol=1e-6)
+        npt.assert_allclose(observed["pvalue"], expected_pvalue, atol=1e-6)
+
     def test_sample_bias(self):
         data = np.log1p(self.table2.to_numpy())
         dmat = dmatrix("group", self.meta2)

EOF_R2E_TEST_PATCH
R2E_APPLY_RC=$?
if [ "$R2E_APPLY_RC" -ne 0 ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  printf '%s' '{"reward": 0.0, "resolved": false, "parse_status": "test_patch_apply_failed"}' > /logs/verifier/reward-details.json
  echo "R2E: test_patch failed to apply (rc=$R2E_APPLY_RC) — failing closed" >&2
  exit 0
fi
( cp -a /opt/skbio-baseline-extensions/. /workspace/ && cd /workspace && python -m pytest -o addopts= -v --tb=short skbio/stats/composition/tests/test_ancombc.py ) > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?
cat /logs/verifier/test_output.log
python3 "$SCRIPT_DIR/verifier.py" --log /logs/verifier/test_output.log --f2p "$SCRIPT_DIR/f2p.json" --p2p "$SCRIPT_DIR/p2p.json" --test-cmds 'cp -a /opt/skbio-baseline-extensions/. /workspace/ && cd /workspace && python -m pytest -o addopts= -v --tb=short skbio/stats/composition/tests/test_ancombc.py' --exit-code "$TEST_EXIT_CODE" --out-dir /logs/verifier || { [ "$TEST_EXIT_CODE" -eq 0 ] && echo "1.0" > /logs/verifier/reward.txt || echo "0.0" > /logs/verifier/reward.txt; }
git checkout 71286a24bddff66c82cb25a7ca13441aa13c2f2c -- skbio/stats/composition/tests/test_ancombc.py || true
exit 0
