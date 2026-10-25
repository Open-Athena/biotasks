#!/usr/bin/env bash
set -eu
cd /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65
export PATH="$PWD/.venv/bin:$PATH"
export UV_CACHE_DIR="$PWD/experiments/65-sealed-case-safe-export/inputs-private/uv-cache"
python -m pytest tests/test_generation_cache_identity.py tests/test_generation_lifecycle.py --basetemp "$PWD/experiments/65-sealed-case-safe-export/inputs-private/pytest-core-003"
