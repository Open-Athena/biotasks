#!/usr/bin/env bash
# Existing approved transport credentials stay in the local controller only.
set -eu
root=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ -z ${CW_KEY_ID:-} || -z ${CW_KEY_SECRET:-} ]]; then
  set -a
  source /home/exedev/.config/coreweave/credentials.env
  set +a
fi
exec "$root/../../../pipeline44/.venv/bin/biotasks" validate run "$root/runs-private/native-001" "$@"
