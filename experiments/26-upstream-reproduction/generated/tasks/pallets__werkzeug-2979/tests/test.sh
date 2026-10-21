#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
git checkout 862cb193c2b13db860d886725fa4235173d0dfcd -- tests/test_datastructures.py || true
git apply --verbose --reject - <<'EOF_R2E_TEST_PATCH'
diff --git a/tests/test_datastructures.py b/tests/test_datastructures.py
index 9d11d2aab..76a5530fc 100644
--- a/tests/test_datastructures.py
+++ b/tests/test_datastructures.py
@@ -258,6 +258,17 @@ def test_basic_interface(self):
         md.setlist("foo", [1, 2])
         assert md.getlist("foo") == [1, 2]
 
+    def test_or(self) -> None:
+        a = self.storage_class({"x": 1})
+        b = a | {"y": 2}
+        assert isinstance(b, self.storage_class)
+        assert "x" in b and "y" in b
+
+    def test_ior(self) -> None:
+        a = self.storage_class({"x": 1})
+        a |= {"y": 2}
+        assert "x" in a and "y" in a
+
 
 class _ImmutableDictTests:
     storage_class: type[dict]
@@ -305,6 +316,17 @@ def test_dict_is_hashable(self):
         assert immutable in x
         assert immutable2 in x
 
+    def test_or(self) -> None:
+        a = self.storage_class({"x": 1})
+        b = a | {"y": 2}
+        assert "x" in b and "y" in b
+
+    def test_ior(self) -> None:
+        a = self.storage_class({"x": 1})
+
+        with pytest.raises(TypeError):
+            a |= {"y": 2}
+
 
 class TestImmutableTypeConversionDict(_ImmutableDictTests):
     storage_class = ds.ImmutableTypeConversionDict
@@ -799,6 +821,17 @@ def test_equality(self):
 
         assert h1 == h2
 
+    def test_or(self) -> None:
+        a = ds.Headers({"x": 1})
+        b = a | {"y": 2}
+        assert isinstance(b, ds.Headers)
+        assert "x" in b and "y" in b
+
+    def test_ior(self) -> None:
+        a = ds.Headers({"x": 1})
+        a |= {"y": 2}
+        assert "x" in a and "y" in a
+
 
 class TestEnvironHeaders:
     storage_class = ds.EnvironHeaders
@@ -840,6 +873,18 @@ def test_return_type_is_str(self):
         assert headers["Foo"] == "\xe2\x9c\x93"
         assert next(iter(headers)) == ("Foo", "\xe2\x9c\x93")
 
+    def test_or(self) -> None:
+        headers = ds.EnvironHeaders({"x": "1"})
+
+        with pytest.raises(TypeError):
+            headers | {"y": "2"}
+
+    def test_ior(self) -> None:
+        headers = ds.EnvironHeaders({})
+
+        with pytest.raises(TypeError):
+            headers |= {"y": "2"}
+
 
 class TestHeaderSet:
     storage_class = ds.HeaderSet
@@ -927,7 +972,7 @@ def test_callback_dict_writes(self):
         assert_calls, func = make_call_asserter()
         initial = {"a": "foo", "b": "bar"}
         dct = self.storage_class(initial=initial, on_update=func)
-        with assert_calls(8, "callback not triggered by write method"):
+        with assert_calls(9, "callback not triggered by write method"):
             # always-write methods
             dct["z"] = 123
             dct["z"] = 123  # must trigger again
@@ -937,6 +982,7 @@ def test_callback_dict_writes(self):
             dct.popitem()
             dct.update([])
             dct.clear()
+            dct |= {}
         with assert_calls(0, "callback triggered by failed del"):
             pytest.raises(KeyError, lambda: dct.__delitem__("x"))
         with assert_calls(0, "callback triggered by failed pop"):

EOF_R2E_TEST_PATCH
R2E_APPLY_RC=$?
if [ "$R2E_APPLY_RC" -ne 0 ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  printf '%s' '{"reward": 0.0, "resolved": false, "parse_status": "test_patch_apply_failed"}' > /logs/verifier/reward-details.json
  echo "R2E: test_patch failed to apply (rc=$R2E_APPLY_RC) — failing closed" >&2
  exit 0
fi
( python -m pytest -v --tb=short /workspace/tests ) > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?
cat /logs/verifier/test_output.log
python3 "$SCRIPT_DIR/verifier.py" --log /logs/verifier/test_output.log --f2p "$SCRIPT_DIR/f2p.json" --p2p "$SCRIPT_DIR/p2p.json" --test-cmds 'python -m pytest -v --tb=short /workspace/tests' --exit-code "$TEST_EXIT_CODE" --out-dir /logs/verifier || { [ "$TEST_EXIT_CODE" -eq 0 ] && echo "1.0" > /logs/verifier/reward.txt || echo "0.0" > /logs/verifier/reward.txt; }
git checkout 862cb193c2b13db860d886725fa4235173d0dfcd -- tests/test_datastructures.py || true
exit 0
