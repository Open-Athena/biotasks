#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
install -m 755 /solution/evaluator.py /workspace/evaluator
/workspace/evaluator evaluate \
  --development /workspace/data/development.csv \
  --holdout /workspace/data/holdout_features.csv \
  --folds /workspace/data/folds.csv \
  --models /workspace/models \
  --output /workspace/output
