#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/reward-details.json
git add -A
git diff --cached 566dbe73c62a13f790713245c24f883d7eb92983 > /tmp/predicted.patch
: 'START_VERIFY_OUTPUT'
python3 "$SCRIPT_DIR/verifier.py" \
    "$SCRIPT_DIR/oracle.patch" \
    /tmp/predicted.patch \
    "$SCRIPT_DIR/instruction.md"
: 'END_VERIFY_OUTPUT'
exit 0
