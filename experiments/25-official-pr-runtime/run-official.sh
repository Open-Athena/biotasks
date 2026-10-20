#!/usr/bin/env bash
# Controller orchestration only; no source, prompt, test or dependency repair.
set -eu
cd /work
mkdir -p bootstrap outputs evidence
archive_evidence() {
    # Only native caches/outputs are archived; gh configuration is never included.
    tar -czf /work/evidence/native-artifacts.tar.gz -C /work bootstrap outputs
}
trap archive_evidence EXIT
python /work/run_native_windows.py
touch /work/native_done
if python -c 'import json; raise SystemExit(not bool(json.load(open("/work/evidence/exported-tasks.json"))))'; then
    # Preserve the live images for official base/oracle controls on this same
    # daemon. The controller stays within its original bounded reservation.
    deadline=$((SECONDS + 7200))
    while [ ! -f /work/controls_done ] && [ "$SECONDS" -lt "$deadline" ]; do
        sleep 10
    done
    if [ ! -f /work/controls_done ]; then
        echo 'Official grading was not completed before the control-stage deadline.' > /work/evidence/controls-unverified.txt
    fi
fi
