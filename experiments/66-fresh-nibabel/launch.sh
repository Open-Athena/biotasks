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
    biotasks66_saved_cw_key_id=${CW_KEY_ID:-}
    biotasks66_saved_cw_key_secret=${CW_KEY_SECRET:-}
    set -a
    . /home/exedev/.config/coreweave/credentials.env
    set +a
    if [ -n "$biotasks66_saved_cw_key_id" ]; then
        export CW_KEY_ID="$biotasks66_saved_cw_key_id"
    fi
    if [ -n "$biotasks66_saved_cw_key_secret" ]; then
        export CW_KEY_SECRET="$biotasks66_saved_cw_key_secret"
    fi
    unset biotasks66_saved_cw_key_id biotasks66_saved_cw_key_secret
fi
test -n "${GH_TOKEN:-}"
test -n "${OPENROUTER_API_KEY:-}"
test -n "${CW_KEY_ID:-}"
test -n "${CW_KEY_SECRET:-}"
case "${1:-run}" in
    check)
        exec gh api repos/nipy/nibabel --jq '{full_name: .full_name, private: .private}'
        ;;
    admit)
        exec /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65/experiments/65-sealed-case-safe-export/inputs-private/candidate-runner/bin/biotasks generate run "$experiment/inputs-private/run-001" --allow-generation --once
        ;;
    run)
        /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65/experiments/65-sealed-case-safe-export/inputs-private/candidate-runner/bin/python -I -B - "$experiment" <<'PY_BASELINE'
import json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve().parents[2] / "65/experiments/65-sealed-case-safe-export"
proof = json.loads((root / "completed-replay-proof.json").read_text())
assert proof["completed_replay_byte_inert"] is True
assert proof["result"]["state"] == "workflow_complete"
for role in ("primary", "cleanup"):
    receipt = json.loads((root / (role + "-hf-receipt.json")).read_text())
    assert receipt["anonymous_download_verified"] is True
PY_BASELINE
        exec /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/65/experiments/65-sealed-case-safe-export/inputs-private/candidate-runner/bin/biotasks generate run "$experiment/inputs-private/run-001" --allow-generation --allow-validation
        ;;
    *) exit 2 ;;
esac
