#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks65_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks65_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks65_saved_cw_key_id" ]; then export CW_KEY_ID="$biotasks65_saved_cw_key_id"; fi
    if [ -n "$biotasks65_saved_cw_key_secret" ]; then export CW_KEY_SECRET="$biotasks65_saved_cw_key_secret"; fi
    unset biotasks65_saved_cw_key_id biotasks65_saved_cw_key_secret
fi
exec "$experiment/inputs-private/candidate-runner/bin/python" -B "$experiment/observe.py" "$@"
