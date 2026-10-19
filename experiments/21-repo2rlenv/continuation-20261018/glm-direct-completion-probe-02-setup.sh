set -e
cd "$IRIS_WORKDIR"
echo 'syncing deps'
uv sync $([ -f uv.lock ] && echo '--frozen' || echo '') --link-mode "${UV_LINK_MODE:-copy}" --python 3.12 --package marin-iris --no-dev
echo 'installing pip deps'
uv pip install --link-mode "${UV_LINK_MODE:-copy}" openai==2.24.0 httpx==0.28.1
