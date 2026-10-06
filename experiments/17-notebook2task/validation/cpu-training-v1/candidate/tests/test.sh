#!/bin/bash
# Verifier runner for the fixed cytopathology model-comparison task.
#
# Uses the Python 3.12 interpreter and pinned scientific packages that are
# pre-installed in the image (numpy==2.3.3, scipy==1.16.2, pandas==2.3.3,
# scikit-learn==1.7.2, pytest==8.4.2). No network access is required at test
# time. The trusted verifier data copy is expected next to this script as
# data.csv (staged by the parent, never copied into the solver image).

set -u

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

if [ ! -f "$TESTS_DIR/data.csv" ]; then
    echo "Error: trusted verifier data copy not found at $TESTS_DIR/data.csv"
    exit 1
fi

mkdir -p /logs/verifier

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
    PY=python
fi

# Single worker/thread so the independent reference fits are reproducible.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

"$PY" -m pytest "$TESTS_DIR/test_outputs.py" -rA --junitxml=/logs/verifier/junit.xml
status=$?

if [ "$status" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
