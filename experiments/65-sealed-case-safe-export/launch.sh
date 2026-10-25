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
"$experiment/inputs-private/candidate-runner/bin/python" -I -B - "$experiment" <<'PY_VERIFY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]); manifest=json.loads((root/'manifest.json').read_text())
assert all(c['mode']=='completed' for c in manifest['cases'])
proof=json.loads((root/'installed-sealed-import-proof.json').read_text())
assert proof['old_generation_and_budget_byte_inert'] and proof['old_generation_run_rejected']
assert proof['native_or_model_calls']==0
PY_VERIFY
# No generation admission and no GH/OpenRouter credential loading.
exec "$experiment/inputs-private/candidate-runner/bin/biotasks" generate run "$experiment/inputs-private/import-001" --allow-validation
