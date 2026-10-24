#!/usr/bin/env bash
set -eu
experiment=$(cd "$(dirname "$0")" && pwd)
project=$experiment/../../../pipeline51
cd "$project"
logs=$experiment/local-checks/installed-001
mkdir "$logs"
exec 9>/tmp/exe-codex-local-heavy.lock
flock -n 9 || exit 75
export POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PATH="$PWD/.venv/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$experiment/inputs-private/candidate-runner"
python - <<'PY' > "$logs/admission.txt"
from pathlib import Path
load = float(Path('/proc/loadavg').read_text().split()[0])
mem = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
assert load < 1.5 and mem >= 2.5 * 1024**3 and mem - 250 * 1024**2 >= 2 * 1024**3
print({'one_minute_load': load, 'mem_available_bytes': mem, 'estimated_peak_bytes': 250 * 1024**2})
PY
date -u +%FT%TZ > "$logs/start.txt"
set +e
/usr/bin/time -v -o "$logs/resources.txt" nice -n 10 ionice -c 2 -n 7 timeout 180 bash -c '
set -e
experiment=$1
uv sync --locked --offline --no-dev --no-install-project --python "$PWD/.venv/bin/python"
uv pip install --offline --no-deps --python "$UV_PROJECT_ENVIRONMENT/bin/python" "$experiment/inputs-private/candidate-artifacts/biotasks-0.1.0-py3-none-any.whl"
unset PYTHONPATH
"$UV_PROJECT_ENVIRONMENT/bin/python" -B "$experiment/prove_supported.py" offline \
  --original "$experiment/../../../47/experiments/47-bootstrap-recipe-state/inputs-private/comparison-001/validation" \
  --output "$experiment/inputs-private/installed-001" \
  --proof "$experiment/installed-offline-proof.json" \
  --prefix research/51-held-retention \
  --reviewed-reference "$experiment/../../../49/experiments/49-native-incomplete-retention/recovery-config.json"
test -f "$experiment/installed-offline-proof.json"
' check "$experiment" > "$logs/output.txt" 2>&1
status=$?
date -u +%FT%TZ > "$logs/end.txt"
printf '%s\n' "$status" > "$logs/exit.txt"
tail -60 "$logs/output.txt"
exit "$status"
