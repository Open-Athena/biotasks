#!/bin/sh
set -eu
cd /work
export DEBIAN_FRONTEND=noninteractive
python -m pip install --disable-pip-version-check uv==0.12.21
export UV_PROJECT_ENVIRONMENT=/work/venv
export UV_PYTHON_DOWNLOADS=never
uv lock --project /work/environment --python "$(command -v python)"
uv sync --project /work/environment --locked --no-dev --no-install-project --python "$(command -v python)"
uv pip freeze --python /work/venv/bin/python > /work/environment/environment.txt
export PATH=/work/venv/bin:$PATH
rm -f /work/setup-inputs.json
sh -eu /work/stage-inputs.sh
