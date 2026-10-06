#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
printf '0\n' > /logs/verifier/reward.txt
export PATH="/opt/venv/bin:/usr/local/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
if [ "$PWD" = / ]; then exit 1; fi
uv pip install --python /opt/venv/bin/python --no-index --find-links /opt/wheels --target /tmp/verifier-deps pytest==8.4.1 pytest-json-ctrf==0.3.5 || exit 1
PYTHONPATH=/tmp/verifier-deps /opt/venv/bin/python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
status=$?
if [ "$status" -eq 0 ]; then printf '1\n' > /logs/verifier/reward.txt; fi
exit "$status"
