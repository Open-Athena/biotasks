#!/usr/bin/env bash
set -eu
cd /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65
export UV_CACHE_DIR="$PWD/experiments/65-sealed-case-safe-export/inputs-private/uv-cache"
/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/58/.venv/bin/uv sync --locked --python /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/58/.venv/bin/python
export PATH="$PWD/.venv/bin:$PATH"
ruff check src tests --fix
ruff format src tests
ty check
python -m pytest tests/test_generation_cache_identity.py tests/test_generation_completed_import.py --basetemp "$PWD/experiments/65-sealed-case-safe-export/inputs-private/pytest-core-001"
