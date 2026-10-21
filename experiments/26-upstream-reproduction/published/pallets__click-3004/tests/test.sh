#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
git checkout a1235aacb1be55dc66ddcfefbf64dec44b6ab54d -- tests/test_options.py || true
git apply --verbose --reject - <<'EOF_R2E_TEST_PATCH'
diff --git a/tests/test_options.py b/tests/test_options.py
index f5017384d8..1e7826d82a 100644
--- a/tests/test_options.py
+++ b/tests/test_options.py
@@ -1,5 +1,10 @@
+import enum
 import os
 import re
+import sys
+
+if sys.version_info < (3, 11):
+    enum.StrEnum = enum.Enum  # type: ignore[assignment]
 
 import pytest
 
@@ -1300,6 +1305,33 @@ def cmd(foo):
     assert result.exit_code == 0
 
 
+class HashType(enum.Enum):
+    MD5 = enum.auto()
+    SHA1 = enum.auto()
+
+
+class Number(enum.IntEnum):
+    ONE = enum.auto()
+    TWO = enum.auto()
+
+
+class Letter(enum.StrEnum):
+    A = enum.auto()
+    B = enum.auto()
+
+
+class Color(enum.Flag):
+    RED = enum.auto()
+    GREEN = enum.auto()
+    BLUE = enum.auto()
+
+
+class ColorInt(enum.IntFlag):
+    RED = enum.auto()
+    GREEN = enum.auto()
+    BLUE = enum.auto()
+
+
 @pytest.mark.parametrize(
     ("choices", "metavars"),
     [
@@ -1308,6 +1340,11 @@ def cmd(foo):
         pytest.param([1.0, 2.0], "[FLOAT]", id="float choices"),
         pytest.param([True, False], "[BOOLEAN]", id="bool choices"),
         pytest.param(["foo", 1], "[TEXT|INTEGER]", id="text/int choices"),
+        pytest.param(HashType, "[HASHTYPE]", id="enum choices"),
+        pytest.param(Number, "[NUMBER]", id="int enum choices"),
+        pytest.param(Letter, "[LETTER]", id="str enum choices"),
+        pytest.param(Color, "[COLOR]", id="flag enum choices"),
+        pytest.param(ColorInt, "[COLORINT]", id="int flag enum choices"),
     ],
 )
 def test_usage_show_choices(runner, choices, metavars):
@@ -1330,12 +1367,61 @@ def cli_without_choices(g):
         pass
 
     result = runner.invoke(cli_with_choices, ["--help"])
-    assert f"[{'|'.join([str(i) for i in choices])}]" in result.output
+    assert (
+        f"[{'|'.join(i.name if isinstance(i, enum.Enum) else str(i) for i in choices)}]"
+        in result.output
+    )
 
     result = runner.invoke(cli_without_choices, ["--help"])
     assert metavars in result.output
 
 
+@pytest.mark.parametrize(
+    ("choices", "default", "default_string"),
+    [
+        (["foo", "bar"], "bar", "bar"),
+        # The default value is not enforced to be in the choices.
+        (["foo", "bar"], "random", "random"),
+        # None cannot be a default value as-is: it left the default value as unset.
+        (["foo", "bar"], None, None),
+        ([0, 1], 0, "0"),
+        # Values are not coerced to the type of the choice, even if equivalent.
+        ([0, 1], 0.0, "0.0"),
+        ([1, 2], 2, "2"),
+        ([1.0, 2.0], 2, "2"),
+        ([1.0, 2.0], 2.0, "2.0"),
+        ([True, False], True, "True"),
+        ([True, False], False, "False"),
+        (["foo", 1], "foo", "foo"),
+        (["foo", 1], 1, "1"),
+        # Enum choices are rendered as their names.
+        # See: https://github.com/pallets/click/issues/2911
+        (HashType, HashType.SHA1, "SHA1"),
+        # Enum choices allow defaults strings that are their names.
+        (HashType, "SHA1", "SHA1"),
+        (Number, Number.TWO, "TWO"),
+        (Letter, Letter.B, "B"),
+        (Color, Color.GREEN, "GREEN"),
+        (ColorInt, ColorInt.GREEN, "GREEN"),
+    ],
+)
+def test_choice_default_rendering(runner, choices, default, default_string):
+    @click.command()
+    @click.option("-g", type=click.Choice(choices), default=default, show_default=True)
+    def cli_with_choices(g):
+        pass
+
+    # Check that the default value is kept normalized to the type of the choice.
+    assert cli_with_choices.params[0].default == default
+
+    result = runner.invoke(cli_with_choices, ["--help"])
+    extra_usage = f"[default: {default_string}]"
+    if default_string is None:
+        assert extra_usage not in result.output
+    else:
+        assert extra_usage in result.output
+
+
 @pytest.mark.parametrize(
     "opts_one,opts_two",
     [

EOF_R2E_TEST_PATCH
R2E_APPLY_RC=$?
if [ "$R2E_APPLY_RC" -ne 0 ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  printf '%s' '{"reward": 0.0, "resolved": false, "parse_status": "test_patch_apply_failed"}' > /logs/verifier/reward.json
  echo "R2E: test_patch failed to apply (rc=$R2E_APPLY_RC) — failing closed" >&2
  exit 0
fi
( cd /workspace && python -m pytest -v tests/test_options.py ) > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?
cat /logs/verifier/test_output.log
python3 "$SCRIPT_DIR/verifier.py" --log /logs/verifier/test_output.log --f2p "$SCRIPT_DIR/f2p.json" --p2p "$SCRIPT_DIR/p2p.json" --test-cmds 'cd /workspace python -m pytest -v tests/test_options.py' --exit-code "$TEST_EXIT_CODE" --out-dir /logs/verifier || { [ "$TEST_EXIT_CODE" -eq 0 ] && echo "1.0" > /logs/verifier/reward.txt || echo "0.0" > /logs/verifier/reward.txt; }
git checkout a1235aacb1be55dc66ddcfefbf64dec44b6ab54d -- tests/test_options.py || true
exit 0
