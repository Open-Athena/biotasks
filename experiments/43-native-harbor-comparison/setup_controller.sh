#!/usr/bin/env bash
set -eu
export DEBIAN_FRONTEND=noninteractive
export TZ=UTC
apt-get update
apt-get install -y --no-install-recommends git ca-certificates
python -m pip install --no-cache-dir uv==0.11.31
python - <<'PY'
from pathlib import Path
import hashlib,json
pins=json.loads(Path('/work/package-pins.json').read_text())
for row in pins['packages']:
 with Path('/work',row['filename']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['wheel_sha256']
tool=json.loads(Path('/work/pins.json').read_text())
with Path('/work/tenacity-9.2.1-py3-none-any.whl').open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==tool['tenacity_wheel_sha256']
PY
uv venv --python /usr/local/bin/python /work/harbor066
uv pip install --python /work/harbor066/bin/python --constraint /work/baseline-constraints.txt /work/harbor-0.6.6-py3-none-any.whl /work/tenacity-9.2.1-py3-none-any.whl
/work/harbor066/bin/harbor --version
uv pip freeze --python /work/harbor066/bin/python > /work/evidence/harbor066-freeze.txt
uv venv --python /usr/local/bin/python /work/harbor024
uv pip install --python /work/harbor024/bin/python /work/harbor-0.24.0-py3-none-any.whl /work/tenacity-9.2.1-py3-none-any.whl
/work/harbor024/bin/harbor --version
uv pip freeze --python /work/harbor024/bin/python > /work/evidence/harbor024-freeze.txt
date --iso-8601=ns > /work/evidence/controller-clock.txt
