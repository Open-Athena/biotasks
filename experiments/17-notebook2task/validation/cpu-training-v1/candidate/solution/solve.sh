#!/bin/bash
# Oracle solution: install the fixed-protocol comparison pipeline at
# /app/run_pipeline.py and execute it end-to-end on the staged dataset.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate the pipeline source next to this script (the oracle run mounts the
# solution directory); fall back to the conventional mount point.
SRC=""
for candidate in "$SCRIPT_DIR/run_pipeline.py" /solution/run_pipeline.py; do
    if [ -f "$candidate" ]; then
        SRC="$candidate"
        break
    fi
done
if [ -z "$SRC" ]; then
    echo "error: run_pipeline.py not found next to solve.sh" >&2
    exit 1
fi

if [ ! -f /app/data/data.csv ]; then
    echo "error: expected dataset at /app/data/data.csv" >&2
    exit 1
fi

mkdir -p /app/results
cp "$SRC" /app/run_pipeline.py

# One worker/thread throughout, for determinism.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

python3 /app/run_pipeline.py --data /app/data/data.csv --output-dir /app/results

# Sanity-check the produced artifacts before finishing.
for artifact in \
    /app/results/oof_predictions.csv \
    /app/results/test_predictions.csv \
    /app/results/folds.csv \
    /app/results/metrics.json \
    /app/results/selected_model_report.json \
    /app/results/eda.json \
    /app/report.md; do
    if [ ! -s "$artifact" ]; then
        echo "error: expected artifact $artifact was not produced" >&2
        exit 1
    fi
done

echo "oracle pipeline completed"
