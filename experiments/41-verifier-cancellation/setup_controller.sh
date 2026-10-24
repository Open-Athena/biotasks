#!/usr/bin/env bash
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git ca-certificates
python -m pip install --no-cache-dir uv==0.11.31
python - <<'PY'
from pathlib import Path
import hashlib,json
pins=json.loads(Path('/work/pins.json').read_text())
for name,key in [('harbor-0.6.6-py3-none-any.whl','harbor_wheel_sha256'),('tenacity-9.2.1-py3-none-any.whl','tenacity_wheel_sha256')]:
 with Path('/work',name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==pins[key]
PY
uv venv --python /usr/local/bin/python /work/harbor066
uv pip install --python /work/harbor066/bin/python /work/harbor-0.6.6-py3-none-any.whl /work/tenacity-9.2.1-py3-none-any.whl
/work/harbor066/bin/harbor --version
uv pip freeze --python /work/harbor066/bin/python > /work/evidence/harbor066-freeze.txt
