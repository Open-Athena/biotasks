"""Locked-environment conversion subprocess; never executes notebook code."""

import json
import sys
from pathlib import Path

from biotasks.notebook_script import UnsupportedNotebook, export_python

source, output = map(Path, sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
try:
    script, receipt = export_python(source)
except UnsupportedNotebook as error:
    (output / "rejection.json").write_text(json.dumps({"reason": str(error)}))
else:
    (output / "baseline.py").write_text(script)
    (output / "conversion.json").write_text(json.dumps(receipt, indent=2) + "\n")
