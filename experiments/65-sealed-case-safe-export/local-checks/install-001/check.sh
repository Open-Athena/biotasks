#!/usr/bin/env bash
set -eu
cd /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65
export UV_CACHE_DIR="$PWD/experiments/65-sealed-case-safe-export/inputs-private/uv-cache"
export UV_PROJECT_ENVIRONMENT="$PWD/experiments/65-sealed-case-safe-export/inputs-private/candidate-runner"
.venv/bin/uv sync --locked --offline --no-dev --no-install-project --python "$PWD/.venv/bin/python"
.venv/bin/uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" --offline --no-deps "$PWD/experiments/65-sealed-case-safe-export/inputs-private/candidate-artifacts/biotasks-0.1.0-py3-none-any.whl"
"$UV_PROJECT_ENVIRONMENT/bin/biotasks" generate identities
