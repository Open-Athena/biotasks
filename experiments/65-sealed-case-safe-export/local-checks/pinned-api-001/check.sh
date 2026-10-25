#!/usr/bin/env bash
set -eu
root=/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees
"$root/58/experiments/58-assertion-regressions/inputs-private/candidate-runner/bin/python" -B "$root/65/experiments/65-sealed-case-safe-export/check_pinned_export.py" original
"$root/65/.venv/bin/python" -B "$root/65/experiments/65-sealed-case-safe-export/check_pinned_export.py" candidate
