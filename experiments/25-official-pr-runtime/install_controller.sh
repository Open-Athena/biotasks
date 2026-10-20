set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git ca-certificates curl
python -m pip install --no-cache-dir uv==0.11.31
curl --fail --location --max-time 120 https://github.com/huggingface/Repo2RLEnv/archive/27d04ee8203cd5b2f20c3997d13836e5f5b64238.tar.gz -o /work/source.tar.gz
echo '9c09729e909766366d8761e71a3585a64f656d1d3c64909b0656a0af28b402e9  /work/source.tar.gz' | sha256sum -c -
mkdir /work/upstream
tar -xzf /work/source.tar.gz -C /work/upstream --strip-components=1
cd /work/upstream
uv sync --frozen --no-dev --extra harbor
curl --fail --location --max-time 120 https://github.com/cli/cli/releases/download/v2.97.0/gh_2.97.0_linux_amd64.tar.gz -o /work/gh.tar.gz
tar -xzf /work/gh.tar.gz -C /work
cp /work/gh_2.97.0_linux_amd64/bin/gh /work/bin/gh
chmod +x /work/bin/docker
export PATH=/work/bin:/work/upstream/.venv/bin:$PATH
export BIOTASKS_REAL_DOCKER=/work/real/docker BIOTASKS_RUN_ID="$BIOTASKS_INSTALL_RUN_ID" BIOTASKS_DOCKER_GUARD_LOCK=/work/docker.lock
repo2rlenv --version
gh --version
harbor --version
python -V
/work/upstream/.venv/bin/python -c 'from pathlib import Path; from repo2rlenv.config import load_generation_input; [load_generation_input(p) for p in Path("/work/inputs").glob("*.json")]; print("All five native configurations validated")'
