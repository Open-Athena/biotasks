#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
export PYTHONPATH="$experiment/../../src"
runner=/home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65/experiments/65-sealed-case-safe-export/inputs-private/candidate-runner/bin/python
if [ -z "${GH_TOKEN:-}" ]; then set -a; . /home/exedev/.codex/secrets/biotasks-github.env; set +a; fi
if [ -z "${OPENROUTER_API_KEY:-}" ]; then set -a; . /home/exedev/.codex/secrets/vepbench.env; set +a; fi
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks67_key_id=${CW_KEY_ID:-}
    biotasks67_key_secret=${CW_KEY_SECRET:-}
    set -a; . /home/exedev/.config/coreweave/credentials.env; set +a
    if [ -n "$biotasks67_key_id" ]; then export CW_KEY_ID="$biotasks67_key_id"; fi
    if [ -n "$biotasks67_key_secret" ]; then export CW_KEY_SECRET="$biotasks67_key_secret"; fi
    unset biotasks67_key_id biotasks67_key_secret
fi
case "${1:-run}" in
 preflight) exec "$runner" "$experiment/preflight.py" ;;
 run) exec "$runner" -m biotasks generate run "$experiment/inputs-private/run-001" --allow-generation --allow-validation ;;
 once) exec "$runner" -m biotasks generate run "$experiment/inputs-private/run-001" --allow-generation --allow-validation --once ;;
 *) exit 2 ;;
esac
