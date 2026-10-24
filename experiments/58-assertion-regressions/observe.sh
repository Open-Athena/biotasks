#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks58_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks58_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks58_saved_cw_key_id" ]; then
        export CW_KEY_ID="$biotasks58_saved_cw_key_id"
    fi
    if [ -n "$biotasks58_saved_cw_key_secret" ]; then
        export CW_KEY_SECRET="$biotasks58_saved_cw_key_secret"
    fi
    unset biotasks58_saved_cw_key_id biotasks58_saved_cw_key_secret
fi
exec "$experiment/inputs-private/candidate-runner/bin/python" -B "$experiment/observe.py" "$@"
