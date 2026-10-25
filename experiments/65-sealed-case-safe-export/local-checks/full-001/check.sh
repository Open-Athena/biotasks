#!/usr/bin/env bash
set -eu
cd /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65
export PATH="$PWD/.venv/bin:$PATH"
export UV_CACHE_DIR="$PWD/experiments/65-sealed-case-safe-export/inputs-private/uv-cache"
export PRE_COMMIT_HOME="$PWD/experiments/65-sealed-case-safe-export/inputs-private/precommit"
python -m pytest --basetemp "$PWD/experiments/65-sealed-case-safe-export/inputs-private/pytest-full-001"
ruff check .
ruff format --check .
ty check
pre-commit run --all-files
biotasks generate identities
