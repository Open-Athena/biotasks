#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks62_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks62_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks62_saved_cw_key_id" ]; then
        export CW_KEY_ID="$biotasks62_saved_cw_key_id"
    fi
    if [ -n "$biotasks62_saved_cw_key_secret" ]; then
        export CW_KEY_SECRET="$biotasks62_saved_cw_key_secret"
    fi
    unset biotasks62_saved_cw_key_id biotasks62_saved_cw_key_secret
fi
exec /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/58/experiments/58-assertion-regressions/inputs-private/candidate-runner/bin/python -B "$experiment/observe.py" "$@"
