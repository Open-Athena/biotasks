#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks57_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks57_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks57_saved_cw_key_id" ]; then
        export CW_KEY_ID="$biotasks57_saved_cw_key_id"
    fi
    if [ -n "$biotasks57_saved_cw_key_secret" ]; then
        export CW_KEY_SECRET="$biotasks57_saved_cw_key_secret"
    fi
    unset biotasks57_saved_cw_key_id biotasks57_saved_cw_key_secret
fi
exec "$experiment/../../../51/experiments/51-held-retention/inputs-private/candidate-runner/bin/python" -B "$experiment/observe.py" "$@"
