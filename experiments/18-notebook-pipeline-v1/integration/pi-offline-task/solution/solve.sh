#!/bin/bash
set -euo pipefail
mkdir -p /output
python3 - <<'PY'
import json
from pathlib import Path
Path('/output/result.json').write_text(json.dumps({'sum':sum(map(int,Path('/input/numbers.txt').read_text().split()))}))
PY
