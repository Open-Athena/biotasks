#!/usr/bin/env bash
set -eu
umask 077
experiment=$(cd "$(dirname "$0")" && pwd)
if [ -z "${GH_TOKEN:-}" ]; then
    set -a
    . /home/exedev/.codex/secrets/biotasks-github.env
    set +a
fi
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    set -a
    . /home/exedev/.codex/secrets/vepbench.env
    set +a
fi
if [ -z "${CW_KEY_ID:-}" ] || [ -z "${CW_KEY_SECRET:-}" ]; then
    biotasks53_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks53_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks53_saved_cw_key_id" ]; then
        export CW_KEY_ID="$biotasks53_saved_cw_key_id"
    fi
    if [ -n "$biotasks53_saved_cw_key_secret" ]; then
        export CW_KEY_SECRET="$biotasks53_saved_cw_key_secret"
    fi
    unset biotasks53_saved_cw_key_id biotasks53_saved_cw_key_secret
fi
test -n "${GH_TOKEN:-}"
test -n "${OPENROUTER_API_KEY:-}"
test -n "${CW_KEY_ID:-}"
test -n "${CW_KEY_SECRET:-}"
case "${1:-run}" in
    check)
        exec gh api repos/scverse/anndata --jq '{full_name: .full_name, private: .private}'
        ;;
    run)
        exec "$experiment/../../../51/experiments/51-held-retention/inputs-private/candidate-runner/bin/biotasks" generate run "$experiment/inputs-private/run-001" --allow-generation --allow-validation
        ;;
    *) exit 2 ;;
esac
