#!/usr/bin/env bash
set -eu
cd /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/pipeline62
export UV_CACHE_DIR=/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/62/experiments/62-fresh-dendropy/inputs-private/promotion-uv-cache
export PRE_COMMIT_HOME=/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/62/experiments/62-fresh-dendropy/inputs-private/promotion-precommit
/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/58/.venv/bin/uv sync --locked --python /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/58/.venv/bin/python
export PATH="$PWD/.venv/bin:$PATH"
python -m pytest
ruff check .
ruff format --check .
ty check
pre-commit run --all-files
biotasks generate identities
