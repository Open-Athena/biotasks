#!/usr/bin/env bash
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git ca-certificates curl
python -m pip install --no-cache-dir uv==0.11.31
python - <<'PY'
import hashlib,json,urllib.request
from pathlib import Path
pins=json.loads(Path('/work/pins.json').read_text())
path=Path('/work/harbor-0.6.6-py3-none-any.whl')
with urllib.request.urlopen(pins['harbor_wheel_url'],timeout=120) as src,path.open('wb') as dst:
 while chunk:=src.read(1024*1024): dst.write(chunk)
assert hashlib.sha256(path.read_bytes()).hexdigest()==pins['harbor_wheel_sha256']
PY
uv venv --python /usr/local/bin/python /work/harbor066
uv pip install --python /work/harbor066/bin/python /work/harbor-0.6.6-py3-none-any.whl
/work/harbor066/bin/harbor --version
uv pip freeze --python /work/harbor066/bin/python > /work/evidence/harbor066-freeze.txt
if [ "$BIOTASKS_PHASE" = generate ]; then
    curl --fail --location --max-time 120 https://github.com/huggingface/Repo2RLEnv/archive/27d04ee8203cd5b2f20c3997d13836e5f5b64238.tar.gz -o /work/source.tar.gz
    echo '9c09729e909766366d8761e71a3585a64f656d1d3c64909b0656a0af28b402e9  /work/source.tar.gz' | sha256sum -c -
    mkdir /work/upstream
    tar -xzf /work/source.tar.gz -C /work/upstream --strip-components=1
    cd /work/upstream
    uv sync --frozen --no-dev --extra harbor
    curl --fail --location --max-time 120 https://github.com/cli/cli/releases/download/v2.97.0/gh_2.97.0_linux_amd64.tar.gz -o /work/gh.tar.gz
    tar -xzf /work/gh.tar.gz -C /work
    cp /work/gh_2.97.0_linux_amd64/bin/gh /work/bin/gh
    /work/bin/gh auth status --hostname github.com >/dev/null 2>&1
    /work/upstream/.venv/bin/repo2rlenv --version
    /work/upstream/.venv/bin/python -c 'from pathlib import Path; from repo2rlenv.config import load_generation_input; [load_generation_input(p) for p in Path("/work/inputs").glob("*.json")]; print("Native configurations validated")'
fi
python -V
/work/real/docker version --format '{{.Client.Version}} / {{.Server.Version}}'
/work/real/docker compose version
